from dataclasses import dataclass, field
from pathlib import Path
from threading import Event
import threading
from typing import Optional

import numpy as np

from application.settings import settings
from framework.file_processing import crop_image_buffer, flip_image_buffer, hdr_merge_mertens_buffer, hdr_merge_robertson_buffer, save_image_buffer


# -----------------
# Reine Konfiguration
# -----------------

@dataclass(slots=True)
class HdrSettings:
    base_tv: float
    hdr_ev: float
    hdr_shots: int

    contrast_weight: float
    exposure_weight: float
    saturation_weight: float

    tonemap_gamma: float

    use_mertens: bool
    use_robertson: bool

@dataclass(slots=True)
class CaptureSettings:
    iso: int
    av: float
    tv: float

    raw_iso: Optional[int] = None
    raw_av: Optional[int] = None
    raw_tv: Optional[int] = None


# -----------------
# Laufzeitstatus
# -----------------


@dataclass(slots=True)
class JobState:
    shot: Event = field(default_factory=Event)
    transferred: Event = field(default_factory=Event)
    processed: Event = field(default_factory=Event)

    start: Optional[float] = None
    end: Optional[float] = None
    error: Optional[str] = None

@dataclass(slots=True)
class ClusterState:
    shot: Event = field(default_factory=Event)
    transferred: Event = field(default_factory=Event)
    processed: Event = field(default_factory=Event)

    formatted: Event = field(default_factory=Event)
    error: Optional[str] = None

@dataclass(slots=True)
class ProjectState:
    total_jobs: int = 0
    finished_jobs: int = 0
    failed_jobs: int = 0
    error: Optional[str] = None


# -----------------
# Objekte
# -----------------


@dataclass(slots=True)
class CameraJob:
    id: str
    cluster_id: str
    project_id: str

    capture: CaptureSettings

    img_buffer: Optional[np.ndarray] = None
    img_destination: Optional[Path] = None

    state: JobState = field(default_factory=JobState)

    def _on_transfer(self):
        threading.Thread(target=self.on_transfer, daemon=True).start()

    def on_transfer(self):
        pass

@dataclass(slots=True)
class CameraJobCluster:
    id: str
    project_id: str

    x: int
    y: int
    bottom: bool # if is True, then should be mirrord after processing to hdr

    hdr: HdrSettings

    img_buffer: Optional[np.ndarray] = None
    img_destination: Optional[Path] = None
    preview_destination: Optional[Path] = None

    auto_format: bool = True
    save_preview: bool = True

    jobs: list[CameraJob] = field(default_factory=list)
    state: ClusterState = field(default_factory=ClusterState)

    def _on_transfer(self):
        threading.Thread(target=self.on_transfer, daemon=True).start()

    def _on_process(self):
        threading.Thread(target=self.on_process, daemon=True).start()

    def on_transfer(self):
        self.process()

    def on_process(self):
        self.format()

    def process(self):
        try:
            images = [job.img_buffer for job in self.jobs if job.img_buffer is not None]

            if len(images) == 0:
                self.state.error = "No job image buffers available"
                return

            # HDR / Einzelbild
            if self.hdr.use_robertson and len(images) >= 2:
                result = hdr_merge_robertson_buffer(
                    images=images,
                    exposure_times=[job.capture.tv for job in self.jobs],
                    gamma=self.hdr.tonemap_gamma,
                )

            elif self.hdr.use_mertens and len(images) >= 2:
                result = hdr_merge_mertens_buffer(
                    images=images,
                    contrast=self.hdr.contrast_weight,
                    exposure=self.hdr.exposure_weight,
                    saturation=self.hdr.saturation_weight,
                )

            else:
                result = images[0].copy()

            if result is None:
                self.state.error = "Image processing failed"
                return

            # Crop
            if settings.app.image_crop > 0:
                cropped = crop_image_buffer(result, settings.app.image_crop)
                if cropped is None:
                    self.state.error = "Image crop failed"
                    return
                result = cropped

            # Bottom drehen
            if self.bottom:
                flipped = flip_image_buffer(result)
                if flipped is None:
                    self.state.error = "Image flip failed"
                    return
                result = flipped

            self.img_buffer = result
            self.state.processed.set()

            if self.auto_format:
                self._on_process()

        except Exception as e:
            self.state.error = str(e)

    def format(self):
        try:
            if self.img_buffer is None:
                self.state.error = "No cluster image buffer to format"
                return

            if self.img_destination is not None:
                saved = save_image_buffer(self.img_buffer, self.img_destination)
                if saved is None:
                    self.state.error = "Saving final image failed"
                    return

            if self.save_preview and self.preview_destination is not None:
                saved_preview = save_image_buffer(self.img_buffer, self.preview_destination)
                if saved_preview is None:
                    self.state.error = "Saving preview image failed"
                    return

            # Job-Zwischendateien löschen, falls vorhanden
            for job in self.jobs:
                if job.img_destination is not None and Path(job.img_destination).exists():
                    try:
                        Path(job.img_destination).unlink()
                    except:
                        pass

            self.state.formatted.set()

        except Exception as e:
            self.state.error = str(e)

@dataclass(slots=True)
class Project:
    id: str

    name: str

    dir_destination: Path
    
    clusters: list[CameraJobCluster] = field(default_factory=list)
    state: ProjectState = field(default_factory=ProjectState)