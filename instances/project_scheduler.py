import time
from typing import *
from threading import Event

from application.settings import settings

from instances.serial_device import SerialDevice
from instances.camera import Camera
from instances.camera_crane import CameraCrane
from instances.turn_table import TurnTable

from instances.threaded_instance import ThreadedInstance

from collections import deque
from concurrent.futures import Future


class SerialDevice(ThreadedInstance):
    def __init__(self, camera: Camera, serial_device: SerialDevice, camera_crane: CameraCrane, turn_table: TurnTable):
        self.camera: Camera = camera
        self.serial_device: SerialDevice = serial_device
        self.camera_crane: CameraCrane = camera_crane
        self.turn_table: TurnTable = turn_table

        self.project_running_event = Event()
        self.project_pause_event = Event()

        self.project_pause_event.set()

        super().__init__()

    def is_project_running(self):
        return self.project_running_event.is_set()

    def is_project_stopped(self):
        return not self.project_running_event.is_set()
    
    def is_project_paused(self):
        return not self.project_pause_event.is_set()


    def start_project(self):
        return
    
    def resume_project(self):
        self.project_pause_event.set()
    
    def pause_project(self):
        self.project_pause_event.clear()
    
    def stop_project(self):
        self.project_pause_event.clear()

    
    def tick(self):
        if not self.camera.is_connected() or not self.serial_device.is_connected():
            return
        
        if not self.project_running_event.is_set():
            # clear cache
            return
        
        self.project_pause_event.wait()