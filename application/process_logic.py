import time
from core.classes.camera import Camera
from projectclasses.ShotPayload import ShotPayload
from utility import conversions
from utility.settings import settings

def create_image_payloads(camera: Camera):
    if camera is None:
        return []
    
    if camera.tv_names is None or len(camera.tv_names) == 0:
        return []
    
    tvs = conversions.generate_hdr_tv_names(
        base_tv=settings.camera.base_tv,
        hdr_shots=settings.camera.hdr_shot_count,
        hdr_ev=settings.camera.hdr_ev,
        tv_names=camera.tv_names,
    )
    
    return [
        ShotPayload(
            iso=settings.camera.iso,
            av=settings.camera.av,
            tv=tv,
        )
        for tv in tvs
    ]