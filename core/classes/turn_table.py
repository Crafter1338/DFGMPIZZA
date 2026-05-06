import logging
import threading
from typing import *
from threading import Event

logger = logging.getLogger(__name__)

from core.classes.serial_orchestrator import *
from core.classes.serial_orchestrator import _generate_rotate_by_instructions, _retrieve_value_from_instruction, SerialOrchestrator, static_instructions
from core.base_worker import BaseWorker
from core.reconnecting_mixin import ReconnectingMixin

class TurnTable(ReconnectingMixin, BaseWorker):
    def __init__(self, serial_orchestrator: SerialOrchestrator):
        super().__init__(name="TurnTable")
        logger.info("TurnTable initialization 1/2")
        self.serial_orchestrator = serial_orchestrator

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

        logger.info("TurnTable initialization 2/2")

    def _null(self):
        logger.info("TurnTable null 1/2")
        
        self.is_nulling = True
        self.end_rotation()

        self.rotated.clear()
        self.nulled.clear()

        self.serial_orchestrator.queue_instructions(static_instructions["table"]["zero"])
        self.serial_orchestrator.queue_instructions(static_instructions["table"]["end"])
        
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
        if not self.serial_orchestrator.is_connected():
            return

        self.serial_orchestrator.queue_instructions(static_instructions["table"]["end"])
        self.is_rotating = False
        self.rotated.clear()

    def rotate_by(self, delta_angle: float):
        if self.is_nulling:
            return

        self.target_rotation = self.rotation + delta_angle
        self.delta_target_rotation = delta_angle

        self.int_target_rotation = int(round(self.target_rotation))
        self.int_delta_target_rotation = int(round(self.delta_target_rotation))

        self.serial_orchestrator.queue_instructions(_generate_rotate_by_instructions(self.int_delta_target_rotation)["SET"])

        self.rotated.clear()
        self.is_rotating = True

    def loop(self):
        self.ensure_connection()
        
        if self.serial_orchestrator is None or not self.serial_orchestrator.is_connected():
            return
        
        if not self.nulled.is_set() and not self.is_nulling:
            self.null()
            return
        
        if not self.nulled.is_set():
            return

        try:
            instructions = _generate_rotate_by_instructions(self.int_delta_target_rotation)
            future = self.serial_orchestrator.queue_instructions(instructions["GET"])
            response = future.result(timeout=1.5)
            
            if response:
                self.rotation = _retrieve_value_from_instruction(response, instructions["factor"], True)
        except Exception as e:
            logger.exception("TurnTable.loop position query error")

        if self.is_rotating and abs(self.target_rotation - self.rotation) < 0.15:
            self.is_rotating = False
            self.rotated.set()