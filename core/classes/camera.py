from dataclasses import dataclass
import logging
import time
import edsdk
import pythoncom
from typing import Optional, Tuple, Deque
from collections import deque
from threading import RLock
from concurrent.futures import Future

from core.base_worker import BaseWorker
from core.reconnecting_mixin import ReconnectingMixin
from projectclasses.ShotPayload import ShotPayload
from utility.settings import settings
import utility.conversions as conversions

logger = logging.getLogger(__name__)

@dataclass
class ShotResult:
    success: bool
    data: bytes | None = None

class Camera(ReconnectingMixin, BaseWorker):
    def __init__(self):
        super().__init__(name="Camera")
        self.cam: Optional[edsdk.EdsObject] = None
        self.is_session_open = False
        
        # State & Queues
        self.busy = False
        self.last_action = time.time()
        self.queue_lock = RLock()
        self.shot_queue: Deque[Tuple[ShotPayload, Future[ShotResult]]] = deque()
        self.pending_settings: Optional[ShotPayload] = None

        # Property Caches (Wichtig für Conversions)
        self.iso_values = []
        self.av_values = []
        self.tv_values = []
        
        self.iso_names: list[int]  = [0, 100, 125, 160, 200, 250, 320, 400, 800, 1000, 1250, 1600, 2000, 2500, 3200, 4000, 5000, 6400, 8000, 10000] # 0 für Auto
        self.tv_names: list[float] = [30, 25, 20, 15, 13, 10, 8, 6, 5, 4, 3.2, 2.5, 2, 1.6, 1.3, 1, 0.8, 0.6, 0.5, 0.4, 0.3, 1/4, 1/5, 1/6, 1/8, 1/10, 1/13, 1/15, 1/20, 1/25, 1/30, 1/40, 1/50, 1/60, 1/80, 1/100, 1/125, 1/160, 1/200, 1/250, 1/320]
        self.av_names: list[float] = [5.6, 6.3, 6.7, 7.1, 8, 8, 9.5, 10, 11, 13, 14, 18, 18, 19, 20, 22, 25]

        # Buffer & Streams
        self.image_data = bytearray(6500 * 4500 * 3)
        self.image_out_stream = None
        
        self.liveview_buffer = bytearray(2048 * 2048 * 3)
        self.liveview_stream = None
        self.liveview_ref = None
        self.last_liveview_time = 0.0

    def on_start(self):
        """Initialisierung im STA Thread."""
        pythoncom.CoInitializeEx(pythoncom.COINIT_APARTMENTTHREADED)
        edsdk.InitializeSDK()
        logger.info("EDSDK Global Initialized")

    def connect(self) -> bool:
        """Verbindungsaufbau zur EOS RP."""
        try:
            cam_list = edsdk.GetCameraList()
            if edsdk.GetChildCount(cam_list) == 0:
                return False
            
            self.cam = edsdk.GetChildAtIndex(cam_list, 0)
            edsdk.OpenSession(self.cam)
            
            # 1. Grundkonfiguration
            edsdk.SetPropertyData(self.cam, edsdk.PropID.SaveTo, 0, edsdk.SaveTo.Host)
            edsdk.SetCapacity(self.cam, {
                "reset": True, 
                "bytesPerSector": 512, 
                "numberOfFreeClusters": 2147483647
            })

            # 2. Property Descriptions laden (für Conversions benötigt)
            self.iso_values = list(edsdk.GetPropertyDesc(self.cam, edsdk.PropID.ISOSpeed)["propDesc"])
            self.av_values = list(edsdk.GetPropertyDesc(self.cam, edsdk.PropID.Av)["propDesc"])
            self.tv_values = list(edsdk.GetPropertyDesc(self.cam, edsdk.PropID.Tv)["propDesc"])

            # 3. Handler & Streams
            edsdk.SetObjectEventHandler(self.cam, edsdk.ObjectEvent.DirItemRequestTransfer, self._handle_transfer)
            self.image_out_stream = edsdk.CreateMemoryStreamFromPointer(self.image_data)

            # 4. State zurücksetzen
            self.busy = False
            with self.queue_lock:
                self.shot_queue.clear()
            self.pending_settings = None

            self.is_session_open = True
            return True
        except Exception:
            return False

    def disconnect(self):
        """Sauberes Beenden der Session."""
        if self.cam:
            try:
                edsdk.CloseSession(self.cam)
            except:
                pass
            self.cam = None
        self.is_session_open = False
        logger.info("Camera disconnected.")

    def enqueue_shot(self, payload: ShotPayload) -> Future[ShotResult]:
        """UI-Schnittstelle: Foto in die Schlange stellen."""
        future = Future[ShotResult]()
        
        with self.queue_lock:
            self.shot_queue.append((payload, future))
        return future

    def enqueue_property_change(self, iso, av, tv):
        """UI-Schnittstelle: Einstellungen ändern ohne Foto"""
        try:
            self.pending_settings = ShotPayload(iso=iso, av=av, tv=tv)
        except Exception:
            pass

    def loop(self):
        """Hauptschleife des Workers."""
        self.ensure_connection()
        if not self.is_session_open:
            return

        # Windows Events verarbeiten (wichtig für Transfer-Callback)
        pythoncom.PumpWaitingMessages()

        # 1. Behandle Pending Settings (UI-Änderungen)
        if not self.busy and self.pending_settings:
            self._apply_settings(self.pending_settings)
            self.pending_settings = None
            
        if not self.busy:
            self._refresh_liveview()

        # 2. Behandle Shot Queue
        if not self.busy:
            with self.queue_lock:
                if self.shot_queue:
                    payload, future = self.shot_queue[0]
                else:
                    payload = None
            if payload is not None:
                self._execute_capture(payload)
                
    def _refresh_liveview(self):
        """Lädt einen neuen Frame von der Kamera herunter."""
        # FPS-Drosselung
        now = time.time()
        if now - self.last_liveview_time < (1.0 / settings.camera.liveview_refresh_rate):
            return

        try:
            # DownloadEvfImage schreibt in den Pointer von self.liveview_buffer
            edsdk.DownloadEvfImage(self.cam, self.liveview_ref)
            self.last_liveview_time = now
        except Exception as e:
            if "EDS_ERR_DEVICE_BUSY" not in str(e):
                logger.debug(f"Liveview übersprungen: {e}")

    def _apply_settings(self, payload: ShotPayload):
        """Überträgt Einstellungen an die Hardware"""
        try:
            payload.prepare_for_camera(self)
            self._set_prop_safe(edsdk.PropID.ISOSpeed, payload.raw_iso)
            self._set_prop_safe(edsdk.PropID.Av, payload.raw_av)
            self._set_prop_safe(edsdk.PropID.Tv, payload.raw_tv)
            self.last_action = time.time()
        except Exception:
            pass

    def _execute_capture(self, payload: ShotPayload): # Prüfen, wenn nicht dann .TakeImage
        """Führt die Aufnahme aus (EOS RP Shutter Logic)"""
        self.busy = True
        self.last_action = time.time()
        try:
            payload.prepare_for_camera(self)
            self._apply_settings(payload)
            
            edsdk.SendCommand(self.cam, edsdk.CameraCommand.PressShutterButton, edsdk.ShutterButton.Halfway)
            time.sleep(0.1)
            edsdk.SendCommand(self.cam, edsdk.CameraCommand.PressShutterButton, edsdk.ShutterButton.Completely)
            edsdk.SendCommand(self.cam, edsdk.CameraCommand.PressShutterButton, edsdk.ShutterButton.OFF)
        except Exception:
            self.busy = False

    def _handle_transfer(self, event, obj_handle, context=None):
        """Callback: Wird vom SDK aufgerufen, wenn Bilddaten bereitliegen."""
        if event != edsdk.ObjectEvent.DirItemRequestTransfer:
            return 0
        
        result = ShotResult(success=False)
        try:
            info = edsdk.GetDirectoryItemInfo(obj_handle)
            edsdk.Download(obj_handle, info["size"], self.image_out_stream)
            edsdk.DownloadComplete(obj_handle)
            raw_bytes = bytes(self.image_data[:info["size"]])
            result = ShotResult(success=True, data=raw_bytes)
            self.image_out_stream = edsdk.CreateMemoryStreamFromPointer(self.image_data)
        except Exception:
            pass
        finally:
            future = None
            with self.queue_lock:
                if self.shot_queue:
                    _, future = self.shot_queue.popleft()
            if future is not None:
                future.set_result(result)
            self.busy = False
        return 0

    def _set_prop_safe(self, prop_id, value, retries=3):
        """Hilfsmethode gegen 'Device Busy' Fehler"""
        for i in range(retries):
            try:
                edsdk.SetPropertyData(self.cam, prop_id, 0, value)
                return
            except Exception:
                if i < retries - 1:
                    time.sleep(0.1)