from core.classes.camera import Camera
from core.classes.camera_crane import CameraCrane
from core.classes.serial_orchestrator import SerialOrchestrator
from core.classes.turn_table import TurnTable

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, List
from threading import Event

from projectclasses.Project import Project
from projectclasses.Image import Image
from projectclasses.ScanPosition import ScanPosition
from projectclasses.ShotPayload import ShotPayload 
from utility.settings import settings

from core.base_worker import BaseWorker

import logging
import time
import threading

logger = logging.getLogger(__name__)

class ProcessOrchestrator(BaseWorker):
    def __init__(self, camera: Camera, serial_orchestrator: SerialOrchestrator, crane: CameraCrane, turntable: TurnTable):
        super().__init__(name="ProcessOrchestrator")
        self.camera = camera
        self.serial_orchestrator = serial_orchestrator
        self.crane = crane
        self.turntable = turntable
        
        self.project: Project = None
            
    def _check_system_ready(self) -> bool:
        try:
            if self.camera is None or self.serial_orchestrator is None or self.crane is None or self.turntable is None:
                return False
            
            if not self.serial_orchestrator.is_connected(): return False
            if not self.serial_orchestrator.is_set_up: return False
            if not self.camera.is_connected(): return False
            if not self.crane.nulled.is_set(): return False
            if not self.turntable.nulled.is_set(): return False
            
            return True
        except:
            return False
    
    def set_project(self, project):
        self.project = project
        
    def loop(self):
        if self.project is None:
            return
        
        self.project.calculate_estimated_time_remaining()
        
        if not self.project.running:
            return
            
        if not self._check_system_ready():
            return
        
        # Nicht wenn auf User Input gewartet wird
        if self.project.turnable and not self.project.turn_confirmed:
            return
        
        if self.project.finished and not self.project.finish_confirmed:
            return
        
        # Projekt Finish Bedingungen
        if self.project.n_finished_scan_positions >= self.project.n_total_scan_positions and not self.project.finished:
            if all(sp.finished for sp in self.project.scan_positions):
                self.project.finished = True
                self.project.stop()
            return
        
        if self.project.index_current >= self.project.n_total_scan_positions and not self.project.finished:
            if all(sp.finished for sp in self.project.scan_positions):
                self.project.finished = True
                self.project.stop()
            return
    
        current_scan_position = self.project.scan_positions[self.project.index_current]
        previous_scan_position = None
        if self.project.index_current != 0:
            previous_scan_position = self.project.scan_positions[self.project.index_current - 1]
        
        if current_scan_position is None:
            return
        
        # Mechanik anfahren
        if current_scan_position.current_shot_indx == 0:
            self.mechanics_move_to_position(current_scan_position, previous_scan_position)
            
            if self.project is not None:
                time.sleep(settings.mechanics.settle_time) # Kleine Kompensation
                
        # Prüfen ob Projekt lebendig ist
        if self.project is None:
            return
        
        # Bild aufnehmen
        self.camera_shoot(current_scan_position)
            
        # Prüfen ob Projekt lebendig ist
        if self.project is None:
            return
            
        if self.project.index_current == self.project.index_turn and not self.project.turn_confirmed:
            self.turntable.rotate_by(360 / settings.process.h_steps) # Drehe nochmal eine Drehung weiter damit der User nicht umdenken muss
            self.turntable.rotated.wait(15)
            self.project.turnable = True # Wenn Index = TurnIndex dann Turnable markieren
            self.project.pause() # Projekt pausieren und auf User Input warten
         
    def camera_shoot(self, scan_position: ScanPosition):
        try:
            if scan_position.current_shot_indx >= len(scan_position.image_payloads):
                logger.warning(
                    "Shot index out of range prevented: %s/%s at project index %s",
                    scan_position.current_shot_indx,
                    len(scan_position.image_payloads),
                    self.project.index_current,
                )
                self.project.index_current += 1
                return

            image_payload = scan_position.image_payloads[scan_position.current_shot_indx]

            result = self.camera.enqueue_shot(image_payload).result(settings.camera.timeout)

            if result is None or not getattr(result, "success", False) or result.data is None:
                return

            scan_position.images.append(Image(data=result.data))
            scan_position.current_shot_indx += 1
            
            if self.project is not None:                
                if scan_position.current_shot_indx >= len(scan_position.image_payloads):
                    self.project.index_current += 1
                    self.project.n_finished_scan_positions += 1
                    
                    threading.Thread(target=scan_position.finish, args=[self], daemon=True).start()

        except Exception as e:
            logger.exception("ProjectScheduler.camera_shoot_image error")
            
    def mechanics_move_to_position(self, scan_position: ScanPosition, prev_scan_position: ScanPosition):
        try:
            logger.debug("Moving to X:%s Y:%s", scan_position.x_pos, scan_position.y_pos)
            
            if prev_scan_position is not None and prev_scan_position.y_pos != scan_position.y_pos:
                self.crane.move_to(scan_position.y_pos)
                
            if prev_scan_position is None:
                self.crane.move_to(scan_position.y_pos)

            if prev_scan_position is not None and prev_scan_position.x_pos != scan_position.x_pos:
                if prev_scan_position.y_pos != scan_position.y_pos:
                    return

                self.turntable.rotate_by(360 / settings.process.h_steps * (-1 if scan_position.flipped else 1))
                self.turntable.rotated.wait()
                            
            while not self.crane.moved.is_set():
                if self.project is None:
                    return
                time.sleep(0.05)

            if self.project is not None and (prev_scan_position is None or prev_scan_position.y_pos != scan_position.y_pos): # Wenn sich y pos ändert
                time.sleep(settings.mechanics.vertical_swing_compensation_delay) # Warte, dass nichts schwingt
        except Exception as e:
            logger.exception("ProjectScheduler.mechanics_move_to_position error")