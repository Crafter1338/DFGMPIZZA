import time
from typing import *
import numpy as np
from threading import Event, RLock

from application.settings import settings
from threaded_instance import ThreadedInstance

from collections import deque
from concurrent.futures import Future

import edsdk

from framework.datastructures import * 
from framework.conversions import * 

import pythoncom

##################################################################

class Camera(ThreadedInstance):
    def __init__(self):
        self.cam: Optional[edsdk.EdsObject] = None

        self.last_connect: float = 0
        self.last_liveview: float = 0
        self.last_busy: float = 0

        self.connected = Event()
        self.connected.clear()
    
        self.busy = False

        self._job_queue: Deque[CameraJob] = deque()
        self.cluster_queue: Deque[CameraJobCluster] = deque()

        self.cluster_buffer: dict[str, CameraJobCluster] = {}

        self.queue_lock = RLock()
    
        super().__init__()

    ##################################################################

    def is_connected(self):
        return self.connected.is_set()
    
    ##################################################################

    def connect(self):
        self.last_connect = time.time()

        try:
            if self.cam:
                self.disconnect()

        except:
            pass

        try:
            camera_list  = edsdk.GetCameraList()
            camera_count = edsdk.GetChildCount(camera_list)

            if camera_count == 0:
                self.connected.clear()
                return
            
            self.cam = edsdk.GetChildAtIndex(camera_list, 0)

            if not self.cam:
                self.connected.clear()
                return
            
            edsdk.OpenSession(self.cam)

            edsdk.SetPropertyData(self.cam, edsdk.PropID.SaveTo, 0, edsdk.SaveTo.Host)
            edsdk.SetPropertyData(self.cam, edsdk.PropID.Evf_OutputDevice, 0, edsdk.EvfOutputDevice.PC)
            edsdk.SetCapacity(
                self.cam, {"reset": True, "bytesPerSector": 512, "numberOfFreeClusters": 2147483647}
            )

            edsdk.SetObjectEventHandler(self.cam, edsdk.ObjectEvent.DirItemRequestTransfer, self.handle_transferring_images)


            self.image_data = bytes(6000*4000*3)    # TODO: Richtige Größe bestimmen
            self.liveview_data = bytes(6000*4000*3) # TODO: Richtige Größe bestimmen

            self.image_out_stream = edsdk.CreateMemoryStreamFromPointer(self.image_data)
            self.liveview_out_stream = edsdk.CreateMemoryStreamFromPointer(self.liveview_data)
            #self.liveview_out_stream = edsdk.CreateFileStream(f"liveview.jpg", edsdk.FileCreateDisposition.CreateAlways, edsdk.Access.ReadWrite)

            self.liveview_ref = edsdk.CreateEvfImageRef(self.liveview_out_stream)

            self.iso_names  = [0, 100, 125, 160, 200, 250, 320, 400, 800, 1000, 1250, 1600, 2000, 2500, 3200, 4000, 5000, 6400, 8000, 10000] # 0 für Auto
            self.tv_names   = [30, 25, 20, 15, 13, 10, 8, 6, 5, 4, 3.2, 2.5, 2, 1.6, 1.3, 1, 0.8, 0.6, 0.5, 0.4, 0.3, 1/4, 1/5, 1/6, 1/8, 1/10, 1/13, 1/15, 1/20, 1/25, 1/30, 1/40, 1/50, 1/60, 1/80, 1/100, 1/125, 1/160, 1/200, 1/250, 1/320]
            self.av_names   = [5.6, 6.3, 6.7, 7.1, 8, 8, 9.5, 10, 11, 13, 14, 18, 18, 19, 20, 22, 25]

            self.iso_values = list(edsdk.GetPropertyDesc(self.cam, edsdk.PropID.ISOSpeed)["propDesc"])
            self.tv_values  = list(edsdk.GetPropertyDesc(self.cam, edsdk.PropID.Tv)["propDesc"])
            self.av_values  = list(edsdk.GetPropertyDesc(self.cam, edsdk.PropID.Av)["propDesc"])

            self.connected.set()
            self.busy = False

        except:
            pass

    def disconnect(self):
        self.connected.clear()

        try:
            edsdk.CloseSession(self.cam)
            self.cam = None
        except:
            pass

    ##################################################################

    def take_image(self, job: CameraJob):
        self.busy = True
        self.last_busy = time.time()

        job.state.start = time.time()

        job.capture.raw_av = round_to_raw_value(
            job.capture.av,
            self.av_names,
            self.av_values
        )

        job.capture.raw_iso = round_to_raw_value(
            job.capture.iso,
            self.iso_names,
            self.iso_values
        )

        job.capture.raw_tv = round_to_raw_value(
            job.capture.tv,
            self.tv_names,
            self.tv_values
        )

        self._job_queue.appendleft(job)

        edsdk.SetPropertyData(self.cam, edsdk.PropID.Tv, 0, job.capture.raw_tv)
        edsdk.SetPropertyData(self.cam, edsdk.PropID.Av, 0, job.capture.raw_av)
        edsdk.SetPropertyData(self.cam, edsdk.PropID.ISOSpeed, 0, job.capture.raw_iso)

        edsdk.SendCommand(self.cam, edsdk.CameraCommand.TakePicture)

        job.state.shot.set()

        pass

    def enqueue_cluster(self, cluster: CameraJobCluster):
        with self.queue_lock:
            self.cluster_queue.append(cluster)

    def handle_transferring_images(self, event, obj_handle):
        if not event == edsdk.ObjectEvent.DirItemRequestTransfer:
            return 0
        
        if not obj_handle:
            return  0
        
        try:
            info = edsdk.GetDirectoryItemInfo(obj_handle)

            job = self._job_queue.popleft()

            edsdk.Download(obj_handle, info["size"], self.image_out_stream)
            edsdk.DownloadComplete(obj_handle)

            jpeg_bytes = bytes(self.image_data[:info["size"]])
            job.img_buffer = np.frombuffer(jpeg_bytes, dtype=np.uint8)

            # optional direkt dekodieren:
            # job.img = cv2.imdecode(job.img_buffer, cv2.IMREAD_COLOR)

            job.state.end = time.time()
            job.state.transferred.set()
            job._on_transfer()

            cluster = self.cluster_buffer.get(job.cluster_id)

            if cluster is not None:
                all_transferred = all(j.state.transferred.is_set() for j in cluster.jobs)

                if all_transferred and not cluster.state.transferred.is_set():
                    cluster.state.transferred.set()
                    cluster._on_transfer()

                    self.cluster_buffer.pop(cluster.id, None)

            self.busy = False

        except Exception as e:
            self.busy = False
            return 0
        
        return 0


    ##################################################################

    def run(self):
        pythoncom.CoInitializeEx(pythoncom.COINIT_APARTMENTTHREADED)
        edsdk.InitializeSDK()

        while not self.is_stopped():
            self.wait_if_paused()

            time.sleep(1/settings.app.thread_refreshrate)

            try:
                if not self.is_connected():
                    if time.time() - self.last_connect > settings.camera.reconnect_delay:
                        self.connect()
                    continue

                if not self.cam:
                    self.disconnect()
                    continue

                if self.busy and time.time() - self.last_busy > settings.camera.timeout:
                    self.disconnect()
                    continue

                pythoncom.PumpWaitingMessages()

                #if self.busy: muss evtl mit unterem getauscht werden
                #    continue

                if time.time() - self.last_liveview > 1/settings.camera.liveview_refresh_rate:
                    self.last_liveview = time.time()
                    edsdk.DownloadEvfImage(self.cam, self.liveview_ref)

                if self.busy:
                    continue

                cluster = None
                with self.queue_lock:
                    if self.cluster_queue:
                        cluster = self.cluster_queue.popleft()

                if cluster is None:
                    continue

                self.cluster_buffer[cluster.id] = cluster

                job = None

                for _job in cluster.jobs:
                    if not _job.state.shot.is_set():
                        job = _job
                        break

                if job:
                    with self.queue_lock:
                        self.cluster_queue.appendleft(cluster)
                else:
                    cluster.state.shot.set()
                    continue

                try:
                    self.take_image(job)

                except Exception as e:
                    with self.queue_lock:
                        self.cluster_queue.appendleft(cluster)

                    self.disconnect()
                    continue

            except Exception as e:
                self.disconnect()

        pythoncom.CoUninitialize()
        edsdk.TerminateSDK()

    ##################################################################

    