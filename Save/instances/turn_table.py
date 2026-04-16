import logging
import threading
from typing import *
from threading import Event

logger = logging.getLogger(__name__)

from instances.serial_device import *
from instances.serial_device import _generate_rotate_by_instructions, _retrieve_value_from_instruction, SerialDevice, static_instructions
from utility.threaded_instance import ThreadedInstance

class TurnTable(ThreadedInstance):
    def __init__(self, serial_device: SerialDevice):
        logger.info("TurnTable initialization 1/2")
        self.serial_device = serial_device

        self.rotation: float = 0
        
        self.target_rotation: float = 0
        self.delta_target_rotation: float = 0

        self.int_target_rotation: int = 0
        self.int_delta_target_rotation: int = 0

        self.rotated = Event()
        self.nulled = Event()

        self.is_rotating = False
        self.is_nulling = False

        self.nulled.clear()
        self.rotated.set()

        super().__init__()
        logger.info("TurnTable initialization 2/2")

    def _null(self):
        logger.info("TurnTable null 1/2")
        
        self.is_nulling = True
        self.end_rotation()

        self.rotated.clear()
        self.nulled.clear()

        self.serial_device.queue_instructions(static_instructions["table"]["zero"])
        self.serial_device.queue_instructions(static_instructions["table"]["end"])
        
        self.rotation = 0
        self.target_rotation = 0
        self.delta_target_rotation = 0

        self.int_target_rotation = 0
        self.int_delta_target_rotation = 0
        
        self.is_nulling = False
        self.nulled.set()

        logger.info("TurnTable null 2/2")

    def null(self):
        if self.is_nulling:
            return

        threading.Thread(target=self._null, daemon=True).start()

    def end_rotation(self):
        if not self.serial_device.is_connected():
            return

        self.serial_device.queue_instructions(static_instructions["table"]["end"])
        self.is_rotating = False
        self.rotated.clear()

    def rotate_by(self, delta_angle: float):
        if self.is_nulling:
            return

        self.target_rotation = self.rotation + delta_angle
        self.delta_target_rotation = delta_angle

        self.int_target_rotation = int(round(self.target_rotation))
        self.int_delta_target_rotation = int(round(self.delta_target_rotation))

        self.serial_device.queue_instructions(_generate_rotate_by_instructions(self.int_delta_target_rotation)["SET"])

        self.rotated.clear()
        self.is_rotating = True

    def tick(self):
        if not self.serial_device.is_set_up:
            self.position: float = 0
            self.target_position: float = 0
            self.int_target_position: int = 0

            self.is_moving = False
            self.is_nulling = False

            self._is_moving_to = False

            self.nulled.clear()
            self.moved.set()
            
        if self.serial_device is None or not self.serial_device.is_connected(): # Wenn Serielle Verbindung nicht besteht
            return
        
        if not self.nulled.is_set() and not self.is_nulling: # Wenn noch nicht kalibriert
            self.null()
            return
        
        if not self.nulled.is_set(): # Während Kalibration
            return

        try:
            instructions = _generate_rotate_by_instructions(self.int_delta_target_rotation)
            future = self.serial_device.queue_instructions(instructions["GET"])
            response = future.result(timeout = 1.5)
            
            if response:
                self.rotation = _retrieve_value_from_instruction(response, instructions["factor"], True)  # Aktuelle Rotation updaten
        except Exception as e:
            logger.exception("TurnTable.tick position query error")

        if self.is_rotating and abs(self.target_rotation - self.rotation) < 0.6:
            self.is_rotating = False
            self.rotated.set()