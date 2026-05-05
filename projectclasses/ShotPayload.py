from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING
from utility.conversions import round_to_raw_value
from utility.settings import settings

if TYPE_CHECKING:
    from core.classes.camera import Camera

@dataclass
class ShotPayload:
    iso: int
    av: float
    tv: float
    
    raw_iso: int = 0
    raw_av: int = 0
    raw_tv: int = 0
    
    def prepare_for_camera(self, camera: Camera) -> None:
        self.raw_iso = round_to_raw_value(self.iso, camera.iso_names, camera.iso_values)
        self.raw_av = round_to_raw_value(self.av, camera.av_names, camera.av_values)
        self.raw_tv = round_to_raw_value(self.tv, camera.tv_names, camera.tv_values)