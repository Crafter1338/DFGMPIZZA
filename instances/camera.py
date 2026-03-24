from dataclasses import dataclass
import time
from typing import *
import edsdk
import numpy as np
import pythoncom
from threading import Event, RLock

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

@dataclass
class ShotResult:
    raw_image_bytes: bytes
    image: datastructures.Image

class Camera(ThreadedInstance):
    def __init__(self):
        self.cam: Optional[edsdk.EdsObject] = None

        self.last_action = time.time()

        self.busy = False

        self.shot_queue: Deque[Tuple[ShotPayload, Future[ShotResult]]] = deque()
        self.queue_lock = RLock()

        self.image_data = bytes(6000 * 4000 * 3) # is a buffer, np.frombuffer, pixmap.loadFromData(buffer, "JPG"), PIL.Image.open(buffer)
        self.liveview_data = bytes(6000 * 4000 * 3)

        self.iso_names: list[int]  = [0, 100, 125, 160, 200, 250, 320, 400, 800, 1000, 1250, 1600, 2000, 2500, 3200, 4000, 5000, 6400, 8000, 10000] # 0 für Auto
        self.tv_names: list[float] = [30, 25, 20, 15, 13, 10, 8, 6, 5, 4, 3.2, 2.5, 2, 1.6, 1.3, 1, 0.8, 0.6, 0.5, 0.4, 0.3, 1/4, 1/5, 1/6, 1/8, 1/10, 1/13, 1/15, 1/20, 1/25, 1/30, 1/40, 1/50, 1/60, 1/80, 1/100, 1/125, 1/160, 1/200, 1/250, 1/320]
        self.av_names: list[float] = [5.6, 6.3, 6.7, 7.1, 8, 8, 9.5, 10, 11, 13, 14, 18, 18, 19, 20, 22, 25]

        self.iso_values: list[int] = []
        self.tv_values: list[int]  = []
        self.av_values: list[int]  = []

        self.last_liveview = 0.0
    
        super().__init__()
    
    def on_start(self):
        self.last_action = time.time()
        pythoncom.CoInitializeEx(pythoncom.COINIT_APARTMENTTHREADED)
        edsdk.InitializeSDK()

    def disconnect(self):
        self.last_action = time.time()
        self.busy = False

        if self.cam:
            edsdk.CloseSession(self.cam)
        self.cam = None

        return True

    def connect(self):
        self.last_action = time.time()

        if self.cam:
            self._disconnect()
            return False

        camera_list  = edsdk.GetCameraList()
        camera_count = edsdk.GetChildCount(camera_list)

        if camera_count == 0:
            self._disconnect()
            return False
        
        self.cam = edsdk.GetChildAtIndex(camera_list, 0)

        if not self.cam:
            self._disconnect()
            return False
        
        edsdk.OpenSession(self.cam)

        edsdk.SetPropertyData(self.cam, edsdk.PropID.SaveTo, 0, edsdk.SaveTo.Host)
        edsdk.SetPropertyData(self.cam, edsdk.PropID.Evf_OutputDevice, 0, edsdk.EvfOutputDevice.PC)
        edsdk.SetCapacity(
            self.cam, {"reset": True, "bytesPerSector": 512, "numberOfFreeClusters": 2147483647}
        )

        edsdk.SetObjectEventHandler(self.cam, edsdk.ObjectEvent.DirItemRequestTransfer, self.handle_transfer)

        self.image_out_stream = edsdk.CreateMemoryStreamFromPointer(self.image_data)
        self.liveview_out_stream = edsdk.CreateMemoryStreamFromPointer(self.liveview_data)

        self.liveview_ref = edsdk.CreateEvfImageRef(self.liveview_out_stream)

        return True
    
    def set_camera_properties(self, iso, av, tv):
        if not self.cam:
            return
        
        if not self.is_connected():
            return
        
        try:
            if self.busy:
                return

            iso = conversions.round_to_raw_value(iso, self.iso_names, self.iso_values)
            av = conversions.round_to_raw_value(av, self.av_names, self.av_values)
            tv = conversions.round_to_raw_value(tv, self.tv_names, self.tv_values)

            edsdk.SetPropertyData(self.cam, edsdk.PropID.Tv, 0, tv)
            edsdk.SetPropertyData(self.cam, edsdk.PropID.Av, 0, av)
            edsdk.SetPropertyData(self.cam, edsdk.PropID.ISOSpeed, 0, iso)
        except:
            pass
    
    def queue_raw_shot(self, iso, av, tv) -> Future[ShotResult]:
        payload = ShotPayload(
            iso=iso,
            av=av,
            tv=tv
        )

        payload.iso = conversions.round_to_raw_value(
            payload.iso,
            self.iso_names,
            self.iso_values
        )

        payload.av = conversions.round_to_raw_value(
            payload.av,
            self.av_names,
            self.av_values
        )

        payload.tv = conversions.round_to_raw_value(
            payload.tv,
            self.tv_names,
            self.tv_values
        )

        future = Future()
        with self.queue_lock:
            self.shot_queue.append((payload, future))

        return future

    def queue_shot(self, payload: ShotPayload) -> Future[ShotResult]:
        payload.iso = conversions.round_to_raw_value(
            payload.iso,
            self.iso_names,
            self.iso_values
        )

        payload.av = conversions.round_to_raw_value(
            payload.av,
            self.av_names,
            self.av_values
        )

        payload.tv = conversions.round_to_raw_value(
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
        
        self.last_action = time.time()
        
        edsdk.SetPropertyData(self.cam, edsdk.PropID.Tv, 0, payload.tv)
        edsdk.SetPropertyData(self.cam, edsdk.PropID.Av, 0, payload.av)
        edsdk.SetPropertyData(self.cam, edsdk.PropID.ISOSpeed, 0, payload.iso)

        edsdk.SendCommand(self.cam, edsdk.CameraCommand.TakePicture)

        self.busy = True

    def handle_transfer(self, event, obj_handle):
        self.last_action = time.time()

        if not event == edsdk.ObjectEvent.DirItemRequestTransfer:
            return 0
        
        if not obj_handle:
            return 0
        
        try:
            info = edsdk.GetDirectoryItemInfo(obj_handle)

            shot_payload, future = self.shot_queue.popleft()

            edsdk.Download(obj_handle, info["size"], self.image_out_stream)
            edsdk.DownloadComplete(obj_handle)

            raw_bytes = bytes(self.image_data[:info["size"]])

            result = ShotResult(
                raw_image_bytes = raw_bytes,
                image = datastructures.Image(data = raw_bytes)
            )

            future.set_result(result)
        except:
            pass

        self.busy = False
        return 0

    def tick(self):
        if not self.cam:
            self._disconnect()
            return
        
        if self.busy and time.time() - self.last_action > settings.camera.timeout:
            self._disconnect()
            return
        
        pythoncom.PumpWaitingMessages()
        
        if time.time() - self.last_liveview > 1/settings.camera.liveview_refresh_rate:
            self.last_liveview = time.time()
            edsdk.DownloadEvfImage(self.cam, self.liveview_ref)

        if self.busy:
            return
        
        if not self.is_connected():
            return

        if self.shot_queue:
            item = None

            with self.queue_lock:
                item = self.shot_queue.popleft()
                self.shot_queue.appendleft(item)

        if not item:
            return
        
        shot_payload, future = item

        self.take_image(shot_payload)
