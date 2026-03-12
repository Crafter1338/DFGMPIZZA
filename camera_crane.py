import threading
import time
from typing import *
from threading import Event

from serial_device import *
from application.settings import settings
from serial_device import _generate_move_to_instructions
from serial_device import _retrieve_value_from_instruction
from threaded_instance import ThreadedInstance

##################################################################

class CameraCrane(ThreadedInstance):
    def __init__(self, serial_device: SerialDevice):
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
        self.moved.clear()

        super().__init__()

    ##################################################################

    def _null(self):
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

    ##################################################################

    def null(self):
        if self.is_nulling:
            return

        threading.Thread(target=self._null, daemon=True).start()

    ##################################################################

    def move_up(self):
        if self.is_nulling:
            return

        return # too dangerous

        if self._is_moving_to: return

        self.serial_device.queue_instructions(static_instructions["arm"]["end"])
        self.serial_device.queue_instructions(static_instructions["arm"]["up"])

        self.is_moving = True
    
    ##################################################################

    def move_down(self):
        if self.is_nulling:
            return
        
        if self._is_moving_to: return

        self.serial_device.queue_instructions(static_instructions["arm"]["end"])
        self.serial_device.queue_instructions(static_instructions["arm"]["down"])

        self.is_moving = True

    ##################################################################

    def move_end(self):
        self.serial_device.queue_instructions(static_instructions["arm"]["end"])

        self.is_moving = False
        self._is_moving_to = False

    ##################################################################

    def move_to(self, pos: float):
        if self.is_nulling:
            return
        
        if self.is_moving and not self._is_moving_to:
            self.move_end()

        pos = min(max(pos, settings.camera_crane.min_pos), settings.camera_crane.max_pos)
        target_position = int(round(pos * 100))
        target_position = min(max(target_position, settings.camera_crane.min_pos*100), settings.camera_crane.max_pos*100)
        
        self.serial_device.queue_instructions(_generate_move_to_instructions(target_position)["SET"])
        
        self.target_position = pos 
        self.int_target_position = target_position

        self.moved.clear()
        self.is_moving = True
        self._is_moving_to = True

    ##################################################################

    def run(self):
        while not self.is_stopped() and not self.serial_device.is_stopped():
            self.wait_if_paused()

            time.sleep(1/settings.app.thread_refreshrate)

            try:
                if not self.serial_device.is_connected():
                    continue

                #if self.is_nulling:
                #    continue

                if not self.nulled.is_set() and not self.is_nulling:
                    self.null()
                    continue

                try:
                    instructions = _generate_move_to_instructions(self.int_target_position)
                    future = self.serial_device.queue_instructions(instructions["GET"])
                    response = future.result(timeout = 1)

                    self.position = (_retrieve_value_from_instruction(response, instructions["factor"]) / 100)
                except Exception as e:
                    continue
                
                if self.is_moving and (self.position >= settings.camera_crane.max_pos or self.position <= settings.camera_crane.min_pos):
                    self.move_end()

                if self.is_moving and abs(self.position - self.target_position) < 0.015:
                    self.is_moving = False
                    self._is_moving_to = False

                    self.move_end()
                    self.moved.set()
            
            except Exception as e:
                pass