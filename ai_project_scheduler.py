import time
from enum import Enum, auto
from pathlib import Path
from threading import Event
from typing import Optional
from uuid import uuid4

from application.settings import settings
from camera import Camera
from camera_crane import CameraCrane
import framework.conversions as conversions
from serial_device import SerialDevice
from threaded_instance import ThreadedInstance
from framework.datastructures import *
from turn_table import TurnTable


class SchedulerPhase(Enum):
    IDLE = auto()
    PREPARE_POSITION = auto()
    WAIT_MECHANICS = auto()
    SETTLE = auto()
    ENQUEUE_CLUSTER = auto()
    WAIT_CLUSTER = auto()
    ADVANCE = auto()
    WAIT_USER_TURN = auto()
    FINISHED = auto()
    ERROR = auto()


class ProjectScheduler(ThreadedInstance):
    def __init__(
        self,
        camera: Camera,
        serial_device: SerialDevice,
        turn_table: TurnTable,
        camera_crane: CameraCrane,
    ):
        self.current_project: Optional[Project] = None

        self.project_running: Event = Event()
        self.project_paused: Event = Event()

        self.current_x: int = 0
        self.current_y: int = 0

        self.current_cluster: Optional[CameraJobCluster] = None

        self.is_bottom: bool = False
        self.can_turn: bool = False

        self.camera: Optional[Camera] = camera
        self.serial_device: Optional[SerialDevice] = serial_device
        self.turn_table: Optional[TurnTable] = turn_table
        self.camera_crane: Optional[CameraCrane] = camera_crane

        self.v_steps = settings.process.v_steps
        self.h_steps = settings.process.h_steps

        self.position_array: list[float] = []
        self.delta_rotation: float = 0.0

        self.phase: SchedulerPhase = SchedulerPhase.IDLE
        self.phase_started_at: float = 0.0
        self.current_settle_delay: float = 0.0

        self._cluster_enqueued: bool = False
        self._cluster_counted: bool = False
        self._pending_row_start_rotation: bool = False

        self.generate_movesets()

        super().__init__()

    ##################################################################
    # Setup / Reset
    ##################################################################

    def generate_movesets(self):
        self.v_steps = max(1, int(settings.process.v_steps))
        self.h_steps = max(1, int(settings.process.h_steps))

        self.position_array = []
        self.delta_rotation = 360 / self.h_steps if self.h_steps > 0 else 360

        if self.v_steps <= 1:
            self.position_array = [0.0]
            return

        stepsize = 1 / (self.v_steps - 1)

        for i in range(self.v_steps):
            self.position_array.append(i * stepsize)

    def reset_runtime_state(self):
        self.current_x = 0
        self.current_y = 0
        self.current_cluster = None

        self.is_bottom = False
        self.can_turn = False

        self.phase = SchedulerPhase.IDLE
        self.phase_started_at = 0.0
        self.current_settle_delay = 0.0

        self._cluster_enqueued = False
        self._cluster_counted = False
        self._pending_row_start_rotation = False

    ##################################################################
    # Project creation
    ##################################################################

    def generate_project(self, name: Optional[str] = None) -> Project:
        self.generate_movesets()

        project_id = str(uuid4())
        project_name = name or f"project_{time.strftime('%Y%m%d_%H%M%S')}"

        destination = Path(settings.process.destination_dir) / project_name
        destination.mkdir(parents=True, exist_ok=True)

        if settings.process.create_previews:
            (destination / "preview").mkdir(parents=True, exist_ok=True)

        total_clusters = self.h_steps * self.v_steps * 2

        is_hdr = settings.camera.use_mertens or settings.camera.use_robertson
        shots_per_cluster = max(1, int(settings.camera.hdr_shot_count)) if is_hdr else 1

        project = Project(
            id=project_id,
            name=project_name,
            dir_destination=destination,
        )

        project.state.total_jobs = total_clusters * shots_per_cluster
        project.state.finished_jobs = 0
        project.state.failed_jobs = 0
        project.state.error = None

        return project

    ##################################################################
    # External control
    ##################################################################

    def start_project(self, project: Project):
        if self.current_project is not None and self.project_running.is_set():
            return

        self.generate_movesets()

        self.current_project = project
        self.project_paused.clear()
        self.project_running.set()

        self.reset_runtime_state()
        self.phase = SchedulerPhase.PREPARE_POSITION
        self.phase_started_at = time.time()

    def pause_project(self):
        if not self.current_project or not self.project_running.is_set():
            return

        self.project_paused.set()

    def resume_project(self):
        if not self.current_project or not self.project_running.is_set():
            return

        self.project_paused.clear()

    def stop_project(self):
        if not self.current_project:
            return

        self.project_running.clear()
        self.project_paused.clear()
        self.reset_runtime_state()

    def confirm_turn_done(self):
        """
        Vom UI aufrufen, wenn der User das Objekt für die zweite Hälfte gedreht hat.
        """
        if self.phase != SchedulerPhase.WAIT_USER_TURN:
            return

        self.can_turn = False
        self.is_bottom = True

        self.current_x = 0
        self.current_y = 0
        self.current_cluster = None

        self._cluster_enqueued = False
        self._cluster_counted = False
        self._pending_row_start_rotation = False

        if self.turn_table and not self.turn_table.is_nulling:
            self.turn_table.null()

        self.phase = SchedulerPhase.PREPARE_POSITION
        self.phase_started_at = time.time()

    ##################################################################
    # Status helpers
    ##################################################################

    def crane_ready(self):
        return (
            self.camera_crane is not None
            and not self.camera_crane.is_moving
            and not self.camera_crane.is_nulling
        )

    def table_ready(self):
        return (
            self.turn_table is not None
            and not self.turn_table.is_rotating
            and not self.turn_table.is_nulling
        )

    def mechanics_ready(self):
        return self.crane_ready() and self.table_ready()

    def cluster_done(self):
        if self.current_cluster is None:
            return False

        state = self.current_cluster.state
        return state.formatted.is_set() or state.transferred.is_set()

    def cluster_failed(self):
        return self.current_cluster is not None and self.current_cluster.state.error is not None

    def current_position_value(self) -> float:
        # oben: 1 -> 0
        # unten: 0 -> 1
        if self.is_bottom:
            return self.position_array[self.current_y]

        return self.position_array[(self.v_steps - 1) - self.current_y]

    def current_rotation_delta(self) -> float:
        return -self.delta_rotation if self.is_bottom else self.delta_rotation

    def current_grid_x(self) -> int:
        return self.current_x + 1

    def current_grid_y(self) -> int:
        return self.current_y + 1 + (self.v_steps if self.is_bottom else 0)

    def total_clusters(self) -> int:
        return self.h_steps * self.v_steps * 2

    def finished_clusters(self) -> int:
        if not self.current_project:
            return 0
        return len(self.current_project.clusters)

    ##################################################################
    # Naming / cluster creation
    ##################################################################

    def make_filename(self) -> str:
        return f"DFGM_R{self.current_grid_y():02d}_C{self.current_grid_x():02d}.jpg"

    def make_preview_filename(self) -> str:
        return f"preview_R{self.current_grid_y():02d}_C{self.current_grid_x():02d}.jpg"

    def build_capture_settings(self) -> list[CaptureSettings]:
        if not self.camera or not self.camera.is_connected():
            return [
                CaptureSettings(
                    iso=settings.camera.iso,
                    av=settings.camera.av,
                    tv=settings.camera.base_tv,
                )
            ]

        is_hdr = settings.camera.use_mertens or settings.camera.use_robertson
        hdr_shots = max(1, int(settings.camera.hdr_shot_count)) if is_hdr else 1

        tv_names = getattr(self.camera, "tv_names", None)
        tv_values = getattr(self.camera, "tv_values", None)
        iso_names = getattr(self.camera, "iso_names", None)
        iso_values = getattr(self.camera, "iso_values", None)
        av_names = getattr(self.camera, "av_names", None)
        av_values = getattr(self.camera, "av_values", None)

        if not tv_names or not tv_values or not iso_names or not iso_values or not av_names or not av_values:
            return [
                CaptureSettings(
                    iso=settings.camera.iso,
                    av=settings.camera.av,
                    tv=settings.camera.base_tv,
                )
                for _ in range(hdr_shots)
            ]

        tv_name_indices = conversions.generate_hdr_tv_name_indices(
            base_tv=settings.camera.base_tv,
            hdr_shots=hdr_shots,
            hdr_ev=settings.camera.hdr_ev,
            tv_names=tv_names,
        )

        captures: list[CaptureSettings] = []

        raw_iso = conversions.round_to_raw_value(
            settings.camera.iso,
            iso_names,
            iso_values,
        )
        raw_av = conversions.round_to_raw_value(
            settings.camera.av,
            av_names,
            av_values,
        )

        for idx in tv_name_indices:
            tv_name = tv_names[idx]
            raw_tv = tv_values[idx]

            captures.append(
                CaptureSettings(
                    iso=settings.camera.iso,
                    av=settings.camera.av,
                    tv=tv_name,
                    raw_iso=raw_iso,
                    raw_av=raw_av,
                    raw_tv=raw_tv,
                )
            )

        return captures

    def build_cluster_for_current_position(self) -> CameraJobCluster:
        if self.current_project is None:
            raise RuntimeError("No active project")

        cluster = CameraJobCluster(
            id=str(uuid4()),
            project_id=self.current_project.id,
            x=self.current_grid_x(),
            y=self.current_grid_y(),
            bottom=self.is_bottom,
            hdr=HdrSettings(
                base_tv=settings.camera.base_tv,
                hdr_ev=settings.camera.hdr_ev,
                hdr_shots=max(1, int(settings.camera.hdr_shot_count)),
                contrast_weight=settings.camera.contrast_weight,
                exposure_weight=settings.camera.exposure_weight,
                saturation_weight=settings.camera.saturation_weight,
                tonemap_gamma=settings.camera.tonemap_gamma,
                use_mertens=settings.camera.use_mertens,
                use_robertson=settings.camera.use_robertson,
            ),
            img_destination=self.current_project.dir_destination / self.make_filename(),
            preview_destination=(
                self.current_project.dir_destination / "preview" / self.make_preview_filename()
                if settings.process.create_previews
                else None
            ),
            auto_format=True,
            save_preview=settings.process.create_previews,
        )

        for capture in self.build_capture_settings():
            cluster.jobs.append(
                CameraJob(
                    id=str(uuid4()),
                    cluster_id=cluster.id,
                    project_id=self.current_project.id,
                    capture=capture,
                    img_destination=cluster.img_destination,
                )
            )

        return cluster

    ##################################################################
    # Flow control
    ##################################################################

    def advance_position(self):
        self.current_cluster = None
        self._cluster_enqueued = False
        self._cluster_counted = False

        self.current_x += 1

        if self.current_x < self.h_steps:
            self.phase = SchedulerPhase.PREPARE_POSITION
            self.phase_started_at = time.time()
            return

        self.current_x = 0
        self.current_y += 1

        if self.current_y < self.v_steps:
            self._pending_row_start_rotation = True
            self.phase = SchedulerPhase.PREPARE_POSITION
            self.phase_started_at = time.time()
            return

        if not self.is_bottom:
            self.can_turn = True
            self.phase = SchedulerPhase.WAIT_USER_TURN
            self.phase_started_at = time.time()
            return

        self.phase = SchedulerPhase.FINISHED
        self.phase_started_at = time.time()

    def _tick_scheduler(self):
        if self.current_project is None:
            self.phase = SchedulerPhase.IDLE
            return

        if self.phase == SchedulerPhase.IDLE:
            return

        if self.phase == SchedulerPhase.PREPARE_POSITION:
            if not self.mechanics_ready():
                return

            should_rotate = self.current_x > 0 or self._pending_row_start_rotation
            if should_rotate and self.turn_table is not None:
                self.turn_table.rotate_by(self.current_rotation_delta())
                self._pending_row_start_rotation = False

            if self.camera_crane is not None:
                self.camera_crane.move_to(self.current_position_value())

            self.phase = SchedulerPhase.WAIT_MECHANICS
            self.phase_started_at = time.time()
            return

        if self.phase == SchedulerPhase.WAIT_MECHANICS:
            if not self.mechanics_ready():
                return

            self.current_settle_delay = settings.mechanics.settle_time

            if self.current_x == 0:
                self.current_settle_delay = max(
                    self.current_settle_delay,
                    settings.mechanics.vertical_swing_compensation_delay,
                )

            self.phase = SchedulerPhase.SETTLE
            self.phase_started_at = time.time()
            return

        if self.phase == SchedulerPhase.SETTLE:
            if (time.time() - self.phase_started_at) < self.current_settle_delay:
                return

            self.phase = SchedulerPhase.ENQUEUE_CLUSTER
            self.phase_started_at = time.time()
            return

        if self.phase == SchedulerPhase.ENQUEUE_CLUSTER:
            if self.current_cluster is None:
                self.current_cluster = self.build_cluster_for_current_position()

            if not self._cluster_enqueued:
                self.current_project.clusters.append(self.current_cluster)
                self.camera.enqueue_cluster(self.current_cluster)
                self._cluster_enqueued = True

            self.phase = SchedulerPhase.WAIT_CLUSTER
            self.phase_started_at = time.time()
            return

        if self.phase == SchedulerPhase.WAIT_CLUSTER:
            if self.current_cluster is None:
                self.phase = SchedulerPhase.ERROR
                self.current_project.state.error = "current_cluster fehlt"
                self.project_running.clear()
                return

            if self.cluster_failed():
                self.current_project.state.error = self.current_cluster.state.error
                self.current_project.state.failed_jobs += len(self.current_cluster.jobs)
                self.phase = SchedulerPhase.ERROR
                self.project_running.clear()
                return

            if not self.cluster_done():
                return

            if not self._cluster_counted:
                self.current_project.state.finished_jobs += len(self.current_cluster.jobs)
                self._cluster_counted = True

            self.phase = SchedulerPhase.ADVANCE
            self.phase_started_at = time.time()
            return

        if self.phase == SchedulerPhase.ADVANCE:
            self.advance_position()
            return

        if self.phase == SchedulerPhase.WAIT_USER_TURN:
            return

        if self.phase == SchedulerPhase.FINISHED:
            self.project_running.clear()
            self.project_paused.clear()
            return

        if self.phase == SchedulerPhase.ERROR:
            self.project_running.clear()
            return

    ##################################################################
    # Thread loop
    ##################################################################

    def run(self):
        while not self.is_stopped():
            self.wait_if_paused()
            time.sleep(1 / settings.app.thread_refreshrate)

            if not self.current_project:
                continue

            if not self.camera or not self.camera_crane or not self.turn_table or not self.serial_device:
                continue

            if not self.camera.is_connected() or not self.serial_device.is_connected():
                continue

            if not self.project_running.is_set():
                continue

            if self.project_paused.is_set():
                continue

            try:
                self._tick_scheduler()
            except Exception as e:
                if self.current_project:
                    self.current_project.state.error = str(e)
                self.phase = SchedulerPhase.ERROR
                self.project_running.clear()