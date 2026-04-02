from dataclasses import dataclass, field
from functools import wraps
from pathlib import Path
import threading
import time
from typing import *
from threading import Event

from application import conversions
from application.datastructures import Image
from application.settings import settings

from instances.serial_device import SerialDevice
from instances.camera import Camera, ShotPayload, ShotResult
from instances.camera_crane import CameraCrane
from instances.turn_table import TurnTable

from instances.threaded_instance import ThreadedInstance

import logging
import traceback
from collections import deque
from concurrent.futures import Future

logger = logging.getLogger(__name__)

import application.file_processing as fp

def cameraready(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        if self.camera is None:
            #logger.warning("Camera missing")
            return None

        if not self.camera.is_connected():
            #logger.debug("Camera not connected")
            return None

        return func(self, *args, **kwargs)
    return wrapper

def mechanicsready(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        if not all([self.serial_device, self.camera_crane, self.turn_table]):
            #logger.warning("Mechanics missing")
            return None

        if not self.serial_device.is_connected():
            #logger.debug("Serial not connected")
            return None

        if not self.camera_crane.nulled.is_set():
            #logger.debug("Crane not nulled")
            return None

        if not self.turn_table.nulled.is_set():
            #logger.debug("Turntable not nulled")
            return None

        return func(self, *args, **kwargs)
    return wrapper

def systemready(func):
    @wraps(func)
    @cameraready
    @mechanicsready
    def wrapper(self, *args, **kwargs):
        return func(self, *args, **kwargs)
    return wrapper

def projectexists(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        if not self.project_running_event.is_set():
            return
        
        if self.current_project is None:
            return
        
        if self.current_project is not None and self.current_project.current_index == self.current_project.turn_index and not self.current_project.turn_confirmed:
            return
        
        if self.current_project is not None and self.current_project.finished:
            return
        
        return func(self, *args, **kwargs)
    return wrapper

@dataclass
class ScanPosition:
    x_pos: float
    y_pos: float
    
    x_name: str
    y_name: str

    flipped: bool

    image_payloads: list[ShotPayload] = field(default_factory=list)
    images: list[Image] = field(default_factory=list)

    final_image: Optional[Image] = None
    
    current_shot_indx: int = 0

    final_image_processed: Event = field(default_factory=Event)

    def process_images(self):
        try:
            cv_images: list = []

            for image in self.images:
                cv_img = image.get_cv2_image()
                if cv_img is None:
                    return False
                cv_images.append(cv_img)

            if len(cv_images) == 0:
                return False

            result = None

            if len(cv_images) == 1:
                result = cv_images[0].copy()

            elif settings.camera.use_mertens:
                result = fp.hdr_merge_mertens_buffer(
                    images=cv_images,
                    contrast=settings.camera.contrast_weight,
                    exposure=settings.camera.exposure_weight,
                    saturation=settings.camera.saturation_weight,
                )

            elif settings.camera.use_robertson:
                exposure_times = [payload.tv for payload in self.image_payloads]

                result = fp.hdr_merge_robertson_buffer(
                    images=cv_images,
                    exposure_times=exposure_times,
                    gamma=settings.camera.tonemap_gamma,
                )

            else:
                result = cv_images[0].copy()

            if result is None:
                return False

            if settings.app.image_crop > 0:
                cropped = fp.crop_image_buffer(result, settings.app.image_crop)
                if cropped is None:
                    return False
                result = cropped

            if self.flipped:
                flipped = fp.flip_image_buffer(result)
                if flipped is None:
                    return False
                result = flipped

            self.final_image = Image()
            self.final_image.cv2_to_data(result)

            self.final_image_processed.set()
        except Exception as e:
            logger.exception("ScanPosition.process_images error")

    def save_final_image(self, project_dir: Path):
        if self.final_image is None:
            return False

        row = int(self.y_name)
        col = int(self.x_name)

        filename = f"DFGM_R{row:02d}_C{col:02d}.jpg"
        final_dst = project_dir / filename

        self.final_image.save_as_file(final_dst)

        if settings.process.create_previews:
            preview_dst = project_dir / "preview" / filename
            self.final_image.save_preview(preview_dst) # did not work

        return True
            
            
@dataclass
class Project:    
    name: str
    dir_destination: Path

    n_finished_shots: int
    n_total_shots: int

    scan_positions: list[ScanPosition] = field(default_factory=list)

    turnable: bool = False
    turn_confirmed: bool = False

    finished: bool = False
    finish_confirmed: bool = False
    
    started_at: float = 0

    current_index: int = 0
    turn_index: int = 0
    
    error: str = 0

class ProjectScheduler(ThreadedInstance):
    def __init__(self, camera: Camera, serial_device: SerialDevice, camera_crane: CameraCrane, turn_table: TurnTable):
        self.camera: Camera = camera
        self.serial_device: SerialDevice = serial_device
        self.camera_crane: CameraCrane = camera_crane
        self.turn_table: TurnTable = turn_table

        self.project_running_event = Event()
        self.project_pause_event = Event()

        self.project_pause_event.set()

        self.current_project: Optional[Project] = None

        super().__init__()

    def is_project_running(self):
        return self.project_running_event.is_set()

    def is_project_stopped(self):
        return not self.project_running_event.is_set()
    
    def is_project_paused(self):
        return not self.project_pause_event.is_set()


    def _create_image_payloads(self) -> list[ShotPayload]:
        if settings.camera.use_mertens or settings.camera.use_robertson:
            tvs = conversions.generate_hdr_tv_names(
                base_tv=settings.camera.base_tv,
                hdr_shots=settings.camera.hdr_shot_count,
                hdr_ev=settings.camera.hdr_ev,
                tv_names=self.camera.tv_names,
            )

            return [
                ShotPayload(
                    iso=settings.camera.iso,
                    av=settings.camera.av,
                    tv=tv,
                )
                for tv in tvs
            ]

        return [
            ShotPayload(
                iso=settings.camera.iso,
                av=settings.camera.av,
                tv=settings.camera.base_tv,
            )
        ]

    def create_project(self, name: str, dst: Path) -> Project:
        try:
            dst = Path(dst) / Path(str(name))
            dst.mkdir(parents=True, exist_ok=True)

            if settings.process.create_previews:
                (dst / "preview").mkdir(parents=True, exist_ok=True)

            h_steps = max(2, int(settings.process.h_steps))
            v_steps = max(2, int(settings.process.v_steps))

            scan_positions = []

            for v_indx in range(v_steps):
                y_pos = 1 - (v_indx / (v_steps-1))

                for h_indx in range(h_steps):
                    x_pos = (h_indx / (h_steps-1)) * 360

                    image_payloads = self._create_image_payloads()

                    scan_positions.append(ScanPosition(
                        image_payloads = image_payloads,
                        x_pos   = x_pos,
                        y_pos   = y_pos,

                        x_name  = str(h_indx + 1),
                        y_name  = str(v_indx + 1),

                        flipped = False,
                    ))

            turn_index = len(scan_positions)

            for v_indx in range(v_steps):
                y_pos = (v_indx / (v_steps-1))

                for h_indx in range(h_steps):
                    x_pos = (h_indx / (h_steps-1)) * 360

                    image_payloads = self._create_image_payloads()

                    scan_positions.append(ScanPosition(
                        image_payloads = image_payloads,
                        x_pos   = x_pos,
                        y_pos   = y_pos,

                        x_name  = str(h_indx + 1),
                        y_name  = str(v_indx + 1 + v_steps),

                        flipped = True,
                    ))

            project = Project(
                name = name,
                dir_destination = dst,

                scan_positions = scan_positions,

                turn_index = turn_index,
                n_total_shots = sum(len(pos.image_payloads) for pos in scan_positions),
                n_finished_shots = 0
            )

            return project
        except Exception as e:
            logger.exception("ProjectScheduler.create_project error")
            return None

    @systemready
    def start_project(self, project):
        if project is None:
            return
        
        self.current_project = project
        self.current_project.started_at = time.time()
        
        if self.current_project is None:
            logger.warning("start_project called with no current project")
            return

        if not self.camera.is_connected() or not self.serial_device.is_connected():
            logger.warning("start_project aborted: camera or serial device not connected")
            return

        logger.info("Starting project %s", self.current_project.name)
        self.current_project.current_index = 0
        self.current_project.n_finished_shots = 0
        self.current_project.turn_confirmed = False
        self.current_project.finished = False

        for pos in self.current_project.scan_positions:
            pos.images.clear()
            pos.current_shot_indx = 0

        self.project_pause_event.set()
        self.project_running_event.set()
    
    def resume_project(self):
        logger.info("Resuming project")
        self.project_pause_event.set()
    
    def pause_project(self):
        logger.info("Pausing project")
        self.project_pause_event.clear()
    
    def stop_project(self):
        logger.info("Stopping project")
        self.project_running_event.clear()
        self.project_pause_event.set()
        
        if self.current_project is None:
            return

        if self.current_project is not None:
            self.current_project.current_index = 0
            self.current_project.turn_confirmed = False
            
        self.camera_crane.move_end()
        self.turn_table.end_rotation()
        
        # TODO: Clear Camera queue?
        
        fp.delete_dir(self.current_project.dir_destination)
        
        self.current_project = None

    def confirm_turn(self):
        if self.current_project is None:
            return
        
        self.current_project.turn_confirmed = True
        
    def confirm_finish(self):
        if self.current_project is None:
            return
        
        self.current_project.finish_confirmed = True
        
        self.current_project = None

    def finish_project(self):
        if self.current_project is None:
            return False

        project = self.current_project

        try:
            for scan_position in project.scan_positions:
                # Falls noch kein Finalbild existiert, aber genug Einzelbilder da sind:
                if scan_position.final_image is None:
                    scan_position.final_image_processed.wait(30)

                # Falls jetzt ein Finalbild vorhanden ist -> speichern
                if scan_position.final_image is not None:
                    scan_position.save_final_image(project.dir_destination)

            project.finished = True
            self.project_running_event.clear()
            self.project_pause_event.set()

            logger.info("Project %s finished", project.name)
            return True

        except Exception as e:
            logger.exception("finish_project error")
            return False
    
    @systemready
    @projectexists
    def tick(self):
        if self.camera is None or self.serial_device is None or self.turn_table is None or self.camera_crane is None:
            logger.warning("Project_Scheduler missing devices")
            return
        
        try:
            self.project_pause_event.wait()

            if self.current_project and self.current_project.current_index >= len(self.current_project.scan_positions):
                self.finish_project()
                return
                
            prev_scan_position: ScanPosition = None
        except Exception as e:
            logger.exception("ProjectScheduler.tick FATAL")
            return

        if self.current_project is not None and self.current_project.current_index != 0:
            prev_scan_position = self.current_project.scan_positions[self.current_project.current_index - 1]

        scan_position = self.current_project.scan_positions[self.current_project.current_index]
        
        if scan_position is None:
            logger.exception("Scan_Position index out of list")
            self.stop_project()

        def camera_shoot_image():
            try:
                if scan_position.current_shot_indx >= len(scan_position.image_payloads):
                    logger.warning(
                        "Shot index out of range prevented: %s/%s at project index %s",
                        scan_position.current_shot_indx,
                        len(scan_position.image_payloads),
                        self.current_project.current_index,
                    )
                    self.current_project.current_index += 1
                    return

                image_payload = scan_position.image_payloads[scan_position.current_shot_indx]

                result = self.camera.queue_shot(image_payload).result(settings.camera.timeout)

                if result is None:
                    return

                scan_position.images.append(result.image)
                scan_position.current_shot_indx += 1
                
                if self.current_project is not None:
                    self.current_project.n_finished_shots += 1
                    
                    if scan_position.current_shot_indx >= len(scan_position.image_payloads):
                        self.current_project.current_index += 1

            except Exception as e:
                logger.exception("ProjectScheduler.camera_shoot_image error")

        def mechanics_move_to_position():
            try:
                logger.debug("Moving to X:%s Y:%s", scan_position.x_pos, scan_position.y_pos)
                
                if prev_scan_position is not None and prev_scan_position.y_pos != scan_position.y_pos:
                    self.camera_crane.move_to(scan_position.y_pos)
                    
                if prev_scan_position is None:
                    self.camera_crane.move_to(scan_position.y_pos)

                if prev_scan_position is not None and prev_scan_position.x_pos != scan_position.x_pos:
                    if self.current_project and self.current_project.current_index == self.current_project.turn_index:
                        return
                    
                    self.turn_table.rotate_by(360 / settings.process.h_steps * (-1 if scan_position.flipped else 1))
                    self.turn_table.rotated.wait()
                                
                self.camera_crane.moved.wait()

                if prev_scan_position is None or prev_scan_position.y_pos != scan_position.y_pos:
                    time.sleep(settings.mechanics.vertical_swing_compensation_delay)
            except Exception as e:
                logger.exception("ProjectScheduler.mechanics_move_to_position error")

        if scan_position.current_shot_indx == 0:
            mechanics_move_to_position()

            time.sleep(settings.mechanics.settle_time)

        camera_shoot_image()
        
        if self.current_project is not None and self.current_project.current_index == self.current_project.turn_index and not self.current_project.turn_confirmed:
            self.current_project.turnable = True
        
        if self.current_project is not None and self.current_project.current_index == self.current_project.turn_index and not self.current_project.turn_confirmed:
            self.turn_table.rotate_by(360 / settings.process.h_steps)
            self.turn_table.rotated.wait(15)

        if len(scan_position.images) == len(scan_position.image_payloads):
            threading.Thread(target=scan_position.process_images, daemon=True).start()