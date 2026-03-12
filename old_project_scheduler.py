import time
from dataclasses import replace
from pathlib import Path
from uuid import uuid4

from application.settings import settings
from framework.conversions import generate_hdr_tv_names
from threaded_instance import ThreadedInstance
from framework.datastructures import *


TV_NAMES = [
    30, 25, 20, 15, 13, 10, 8, 6, 5, 4, 3.2, 2.5, 2, 1.6, 1.3, 1,
    0.8, 0.6, 0.5, 0.4, 0.3, 1/4, 1/5, 1/6, 1/8, 1/10, 1/13, 1/15,
    1/20, 1/25, 1/30, 1/40, 1/50, 1/60, 1/80, 1/100, 1/125, 1/160,
    1/200, 1/250, 1/320
]


class ProjectScheduler(ThreadedInstance):
    def __init__(self):
        self.project: Project | None = None
        super().__init__()

    def generate_project(self, name: str) -> Project:
        project_id = uuid4().hex

        project_dir = Path(settings.process.destination_dir) / name
        preview_dir = project_dir / "preview"

        project_dir.mkdir(parents=True, exist_ok=True)

        if settings.process.create_previews:
            preview_dir.mkdir(parents=True, exist_ok=True)

        hdr = HdrSettings(
            base_tv=settings.camera.base_tv,
            hdr_ev=settings.camera.hdr_ev,
            hdr_shots=settings.camera.hdr_shot_count,
            contrast_weight=settings.camera.contrast_weight,
            exposure_weight=settings.camera.exposure_weight,
            saturation_weight=settings.camera.saturation_weight,
            tonemap_gamma=settings.camera.tonemap_gamma,
            use_mertens=settings.camera.use_mertens,
            use_robertson=settings.camera.use_robertson,
        )

        if settings.camera.use_robertson or settings.camera.use_mertens:
            tv_values = generate_hdr_tv_names(
                base_tv=hdr.base_tv,
                hdr_shots=hdr.hdr_shots,
                hdr_ev=hdr.hdr_ev,
                tv_names=TV_NAMES,
            )
        else:
            tv_values = [hdr.base_tv]

        clusters: list[CameraJobCluster] = []

        h_steps = settings.process.h_steps
        v_steps = settings.process.v_steps

        def build_cluster(x: int, y: int, bottom: bool) -> CameraJobCluster:
            cluster_id = uuid4().hex

            row_no = y + 1
            col_no = x + 1

            final_filename = f"DFGM_R{row_no:02d}_C{col_no:02d}.jpg"
            preview_filename = f"DFGM_R{row_no:02d}_C{col_no:02d}.jpg"

            cluster = CameraJobCluster(
                id=cluster_id,
                project_id=project_id,
                x=x,
                y=y,
                bottom=bottom,
                hdr=replace(hdr),
                img_destination=project_dir / final_filename,
                preview_destination=(preview_dir / preview_filename) if settings.process.create_previews else None,
                auto_format=True,
                save_preview=settings.process.create_previews,
            )

            for shot_index, tv in enumerate(tv_values, start=1):
                job_id = uuid4().hex

                job = CameraJob(
                    id=job_id,
                    cluster_id=cluster_id,
                    project_id=project_id,
                    capture=CaptureSettings(
                        iso=settings.camera.iso,
                        av=settings.camera.av,
                        tv=tv,
                    ),
                    img_destination=project_dir / f"{cluster_id}_S{shot_index:02d}.jpg",
                )

                cluster.jobs.append(job)

            return cluster

        # top side
        for y in range(v_steps):
            for x in range(h_steps):
                clusters.append(build_cluster(x=x, y=y, bottom=False))

        # bottom side
        for y in range(v_steps):
            for x in range(h_steps):
                clusters.append(build_cluster(x=x, y=v_steps + y, bottom=True))

        return Project(
            id=project_id,
            name=name,
            dir_destination=project_dir,
            clusters=clusters,
            state=ProjectState(
                total_jobs=sum(len(cluster.jobs) for cluster in clusters),
            ),
        )

    def run_project(self, project: Project):
        self.project = project

    def run(self): # as for this function, I mean: it should also do the moving to the expected positions
        # for the top half: start at 100% cameracrane and end at 0% cameracrane
        # rotate by + 360/v_steps for each x
        # 

        # for bottom half:
        # start at 0% and go up to 100% cameracrane
        # rotate by -360/v_steps for each x
        while not self.is_stopped():
            self.wait_if_paused()
            time.sleep(1 / settings.app.thread_refreshrate)

            if self.project is None:
                continue

            project = self.project

            try:
                all_done = True

                for cluster in project.clusters:
                    if cluster.state.formatted.is_set():
                        continue

                    cluster_ready = all(job.state.transferred.is_set() for job in cluster.jobs)

                    if not cluster_ready:
                        all_done = False
                        continue

                    if not cluster.state.transferred.is_set():
                        cluster.state.transferred.set()
                        cluster._on_transfer()

                    if not cluster.state.formatted.is_set():
                        all_done = False

                finished_jobs = 0
                failed_jobs = 0

                for cluster in project.clusters:
                    for job in cluster.jobs:
                        if job.state.transferred.is_set():
                            finished_jobs += 1
                        if job.state.error is not None:
                            failed_jobs += 1

                    if cluster.state.error is not None:
                        failed_jobs += len([job for job in cluster.jobs if job.state.error is None])

                project.state.finished_jobs = finished_jobs
                project.state.failed_jobs = failed_jobs

                if all_done:
                    self.project = None

            except Exception as e:
                project.state.error = str(e)