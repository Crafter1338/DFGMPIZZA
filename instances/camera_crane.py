import logging
import threading
import time
from typing import *
from threading import Event

logger = logging.getLogger(__name__)

from instances.serial_device import _generate_move_to_instructions, _retrieve_value_from_instruction, SerialDevice, static_instructions
from application.settings import settings
from instances.threaded_instance import ThreadedInstance

class CameraCrane(ThreadedInstance):
    def __init__(self, serial_device: SerialDevice):
        logger.info("CameraCrane initialization 1/2")
        self.serial_device = serial_device

        self.position: float = 0
        self.target_position: float = 0
        self.int_target_position: int = 0

        self.moved = Event()
        self.nulled = Event()

        self.is_moving = False
        self.is_nulling = False

        self._is_moving_to = False

        self.nulled.clear()
        self.moved.set()

        super().__init__()
        logger.info("CameraCrane initialization 2/2")

    def _null(self): # Kalibrationsfahrt des Schwenkarms
        logger.info("CameraCrane null 1/2")
        self.is_nulling = True
        self.is_moving = False
        self._is_moving_to = False

        self.move_end()

        self.moved.clear()
        self.nulled.clear()

        self.serial_device.queue_instructions(static_instructions["arm"]["down"])
        time.sleep(max(settings.camera_crane.homing_duration or 60, 40))
        self.serial_device.queue_instructions(static_instructions["arm"]["end"])

        self.is_nulling = False
        self.nulled.set()
        self.position = 0
        logger.info("CameraCrane null 2/2")

    def null(self):
        if self.is_nulling:
            return

        threading.Thread(target=self._null, daemon=True).start()

    def move_up(self):
        if self.is_nulling:
            return

        return # zu gefährlich (kann unter bestimmten Bedingungen für immer steigen)

        if self._is_moving_to: return

        self.serial_device.queue_instructions(static_instructions["arm"]["end"])
        self.serial_device.queue_instructions(static_instructions["arm"]["up"])

        self.is_moving = True

    def move_down(self):
        if self.is_nulling:
            return
        
        logger.info("CameraCrane moving down")
        
        if self._is_moving_to: return

        self.serial_device.queue_instructions(static_instructions["arm"]["end"])
        self.serial_device.queue_instructions(static_instructions["arm"]["down"])

        self.is_moving = True

    def move_end(self):
        logger.info("CameraCrane move_end")

        self.serial_device.queue_instructions(static_instructions["arm"]["end"])

        self.is_moving = False
        self._is_moving_to = False

    def move_to(self, pos: float):
        logger.info("CameraCrane move_to 1/3: pos=%s", pos)

        if not self.nulled.is_set():
            return
        
        if self.is_nulling:
            return
        
        if self.is_moving and not self._is_moving_to:
            self.move_end()

        pos = pos * (settings.camera_crane.max_pos - settings.camera_crane.min_pos) + settings.camera_crane.min_pos

        pos = min(max(pos, settings.camera_crane.min_pos), settings.camera_crane.max_pos)
        target_position = int(round(pos * 100))
        target_position = min(max(target_position, settings.camera_crane.min_pos*100), settings.camera_crane.max_pos*100)

        logger.info("CameraCrane move_to position calculated 2/3: target=%s", target_position)
        
        self.serial_device.queue_instructions(_generate_move_to_instructions(target_position)["SET"])
        
        self.target_position = pos 
        self.int_target_position = target_position

        self.moved.clear()
        self.is_moving = True
        self._is_moving_to = True

        logger.info("CameraCrane move_to position set 3/3: target=%s", target_position)

    def tick(self):
        if not self.serial_device or not self.serial_device.is_connected(): # Wenn Serielle Verbindung nicht besteht
            return
        
        if not self.nulled.is_set() and not self.is_nulling: # Wenn noch nicht kalibriert
            self.null()
            return
        
        if not self.nulled.is_set(): # Wenn gerade kalibriert wird
            return

        try:
            instructions = _generate_move_to_instructions(self.int_target_position)
            future = self.serial_device.queue_instructions(instructions["GET"])
            response = future.result(timeout = 1.5)

            if response:
                self.position = (_retrieve_value_from_instruction(response, instructions["factor"]) / 100) # Aktuelle Position updaten
        except Exception as e:
            logger.exception("CameraCrane.tick position query error")
            return
        
        if self.is_moving and not self._is_moving_to and (self.position >= settings.camera_crane.max_pos or self.position <= settings.camera_crane.min_pos):
            self.move_end()

        if self.is_moving and abs(self.position - self.target_position) < 0.015:
            self.is_moving = False
            self._is_moving_to = False

            self.move_end()
            self.moved.set()