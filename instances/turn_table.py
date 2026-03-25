import threading
import time
from typing import *
from threading import Event

from instances.serial_device import *
from application.settings import settings
from instances.serial_device import _generate_rotate_by_instructions, _retrieve_value_from_instruction, SerialDevice, static_instructions
from instances.threaded_instance import ThreadedInstance

class TurnTable(ThreadedInstance):
    def __init__(self, serial_device: SerialDevice):
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

    def _null(self):
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
        if not self.serial_device or not self.serial_device.is_connected():
            return
        
        if not self.nulled.is_set() and not self.is_nulling:
            self.null()
            return

        try:
            instructions = _generate_rotate_by_instructions(self.int_delta_target_rotation)
            future = self.serial_device.queue_instructions(instructions["GET"])
            response = future.result(timeout = 5)
            
            self.rotation = _retrieve_value_from_instruction(response, instructions["factor"], True)
        except Exception as e:
            pass

        if self.is_rotating and abs(self.target_rotation - self.rotation) < 0.6:
            self.is_rotating = False
            self.rotated.set()