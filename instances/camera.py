from dataclasses import dataclass
import logging
import time
from typing import *
import edsdk
import numpy as np
import pythoncom
from threading import Event, RLock

logger = logging.getLogger(__name__)

from application.settings import settings
from instances.threaded_instance import ThreadedInstance

from collections import deque
from concurrent.futures import Future

from application import datastructures

import application.conversions as conversions

@dataclass
class ShotPayload:
    iso: int
    av: float
    tv: float
    
    raw_iso: int = 0
    raw_av: int = 0
    raw_tv: int = 0

@dataclass
class ShotResult:
    raw_image_bytes: bytes
    image: datastructures.Image

class Camera(ThreadedInstance):
    def __init__(self):
        logger.info("Camera initialization 1/2")
        self.cam: Optional[edsdk.EdsObject] = None

        self.last_action = time.time()

        self.busy = False

        self.shot_queue: Deque[Tuple[ShotPayload, Future[ShotResult]]] = deque()
        self.queue_lock = RLock()

        self.image_data = bytearray(6000 * 4000 * 3) # is a buffer, np.frombuffer, pixmap.loadFromData(buffer, "JPG"), PIL.Image.open(buffer)
        self.liveview_data = bytearray(6000 * 4000 * 3)

        self.iso_names: list[int]  = [0, 100, 125, 160, 200, 250, 320, 400, 800, 1000, 1250, 1600, 2000, 2500, 3200, 4000, 5000, 6400, 8000, 10000] # 0 für Auto
        self.tv_names: list[float] = [30, 25, 20, 15, 13, 10, 8, 6, 5, 4, 3.2, 2.5, 2, 1.6, 1.3, 1, 0.8, 0.6, 0.5, 0.4, 0.3, 1/4, 1/5, 1/6, 1/8, 1/10, 1/13, 1/15, 1/20, 1/25, 1/30, 1/40, 1/50, 1/60, 1/80, 1/100, 1/125, 1/160, 1/200, 1/250, 1/320]
        self.av_names: list[float] = [5.6, 6.3, 6.7, 7.1, 8, 8, 9.5, 10, 11, 13, 14, 18, 18, 19, 20, 22, 25]

        self.iso_values: list[int] = []
        self.tv_values: list[int]  = []
        self.av_values: list[int]  = []

        self.last_liveview = 0.0
    
        super().__init__()
        logger.info("Camera initialization 2/2")
    
    def on_start(self):
        try:
            self.last_action = time.time()
            pythoncom.CoInitializeEx(pythoncom.COINIT_APARTMENTTHREADED) # pythoncom für background thread
            edsdk.InitializeSDK() # EDSDK Init

            logger.info("Camera EDSDK initialized")
        except Exception as e:
            logger.exception("Camera.on_start error")

    def disconnect(self):
        logger.info("Camera disconnected")

        self.last_action = time.time()
        self.busy = False

        if self.cam:
            edsdk.CloseSession(self.cam)
        self.cam = None

        return True

    def connect(self): # Verbindung zur Kamera herstellen
        logger.info("Camera connecting... 1/5")

        self.last_action = time.time()

        if self.cam:
            self._disconnect()
            return False

        camera_list  = edsdk.GetCameraList()
        camera_count = edsdk.GetChildCount(camera_list)

        logger.info("Camera connecting... 2/5")

        if camera_count == 0:
            return False
        
        self.cam = edsdk.GetChildAtIndex(camera_list, 0)

        if not self.cam:
            self._disconnect()
            return False
        
        logger.info("Camera connecting... 3/5")
        
        edsdk.OpenSession(self.cam)
        
        logger.info("Camera connecting... 4/5")

        time.sleep(1)

        edsdk.SetPropertyData(self.cam, edsdk.PropID.SaveTo, 0, edsdk.SaveTo.Host)
        edsdk.SetPropertyData(self.cam, edsdk.PropID.Evf_OutputDevice, 0, edsdk.EvfOutputDevice.PC)
        edsdk.SetCapacity(
            self.cam, {"reset": True, "bytesPerSector": 512, "numberOfFreeClusters": 2147483647}
        )

        edsdk.SetObjectEventHandler(self.cam, edsdk.ObjectEvent.DirItemRequestTransfer, self.handle_transfer)

        self.iso_values = list(edsdk.GetPropertyDesc(self.cam, edsdk.PropID.ISOSpeed)["propDesc"])
        self.av_values = list(edsdk.GetPropertyDesc(self.cam, edsdk.PropID.Av)["propDesc"])
        self.tv_values = list(edsdk.GetPropertyDesc(self.cam, edsdk.PropID.Tv)["propDesc"])

        self.image_out_stream = edsdk.CreateMemoryStreamFromPointer(self.image_data)
        self.liveview_out_stream = edsdk.CreateMemoryStreamFromPointer(self.liveview_data)

        self.liveview_ref = edsdk.CreateEvfImageRef(self.liveview_out_stream)

        logger.info("Camera connected")

        return True
    
    def set_camera_properties(self, iso, av, tv):
        if not self.cam:
            return
        
        if not self.is_connected():
            return
    
        if self.busy:
            return

        try:
            iso = conversions.round_to_raw_value(iso, self.iso_names, self.iso_values)
            av = conversions.round_to_raw_value(av, self.av_names, self.av_values)
            tv = conversions.round_to_raw_value(tv, self.tv_names, self.tv_values)
            
            edsdk.SetPropertyData(self.cam, edsdk.PropID.Tv, 0, int(tv))
            edsdk.SetPropertyData(self.cam, edsdk.PropID.Av, 0, int(av))
            edsdk.SetPropertyData(self.cam, edsdk.PropID.ISOSpeed, 0, int(iso))
        except Exception as e:
            logger.exception("Camera.set_camera_properties error")
            pass

    def queue_shot(self, payload: ShotPayload) -> Future[ShotResult]:
        payload.raw_iso = conversions.round_to_raw_value(
            payload.iso,
            self.iso_names,
            self.iso_values
        )
        
        payload.raw_av = conversions.round_to_raw_value(
            payload.av,
            self.av_names,
            self.av_values
        )

        payload.raw_tv = conversions.round_to_raw_value(
            payload.tv,
            self.tv_names,
            self.tv_values
        )
    
        future = Future()
        with self.queue_lock:
            self.shot_queue.append((payload, future))

        return future
    
    def take_image(self, payload: ShotPayload):
        if not self.cam:
            return
        
        if not self.is_connected():
            return
        
        if not payload.raw_av or not payload.raw_iso or not payload.raw_tv:
            return
        
        logger.debug("Camera take_image start")
        
        self.last_action = time.time()
        
        try:
            edsdk.SetPropertyData(self.cam, edsdk.PropID.Tv, 0, payload.raw_tv)
            edsdk.SetPropertyData(self.cam, edsdk.PropID.Av, 0, payload.raw_av)
            edsdk.SetPropertyData(self.cam, edsdk.PropID.ISOSpeed, 0, payload.raw_iso)

            edsdk.SendCommand(self.cam, edsdk.CameraCommand.TakePicture, 0)

            self.busy = True
        except Exception as e:
            # TODO: If error is autofocus then find out fix
            return

        logger.debug("Camera take_image complete")

    def handle_transfer(self, event, obj_handle): # Empfängt das Bild und schreibt es in den Buffer
        self.last_action = time.time()

        logger.debug("Camera.handle_transfer start")

        if not event == edsdk.ObjectEvent.DirItemRequestTransfer:
            return 0
        
        if not obj_handle:
            return 0
        
        try:
            info = edsdk.GetDirectoryItemInfo(obj_handle)

            shot_payload, future = self.shot_queue.popleft()

            time.sleep(0.5)

            edsdk.Download(obj_handle, info["size"], self.image_out_stream)
            edsdk.DownloadComplete(obj_handle)

            raw_bytes = bytes(self.image_data[:info["size"]])

            result = ShotResult(
                raw_image_bytes = raw_bytes,
                image = datastructures.Image(data = raw_bytes)
            )

            future.set_result(result)

            logger.debug("Camera.handle_transfer complete")
            
            self.image_out_stream = edsdk.CreateMemoryStreamFromPointer(self.image_data)
            self.liveview_out_stream = edsdk.CreateMemoryStreamFromPointer(self.liveview_data)

            self.liveview_ref = edsdk.CreateEvfImageRef(self.liveview_out_stream)
        except Exception as e:
            logger.exception("Camera.handle_transfer error")

        self.busy = False
        return 0

    def tick(self):             
        if self.busy and time.time() - self.last_action > settings.camera.timeout:
            self._disconnect()
            return
        
        pythoncom.PumpWaitingMessages() # Ohne das hier kommen keine Bilder an
        
        if self.busy:
            return
        
        if not self.is_connected():
            return
        
        if time.time() - self.last_liveview > 1/settings.camera.liveview_refresh_rate:
            self.last_liveview = time.time()
            edsdk.DownloadEvfImage(self.cam, self.liveview_ref)
        

        item = None
            
        if self.shot_queue:
            with self.queue_lock:
                item = self.shot_queue.popleft()
                self.shot_queue.appendleft(item)

        if not item:
            return
        
        shot_payload, future = item

        self.take_image(shot_payload)
