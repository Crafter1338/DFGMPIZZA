import time
from dataclasses import replace
from pathlib import Path
from uuid import uuid4

from application.settings import settings
from camera import Camera
from camera_crane import CameraCrane
import framework.conversions as conversions
from serial_device import SerialDevice
from threaded_instance import ThreadedInstance
from framework.datastructures import *
from turn_table import TurnTable

class ProjectScheduler(ThreadedInstance):
    def __init__(self, camera: Camera, serial_device: SerialDevice, turn_table: TurnTable, camera_crane: CameraCrane):
        self.current_project: Optional[Project] = None

        self.project_running: Event = Event()
        self.project_paused: Event = Event()

        self.current_x: int = 0
        self.current_y: int = 0

        self.current_cluster: Optional[CameraJobCluster] = None 

        self.is_bottom: bool = False
        self.can_turn: bool = False

        self.camera: Optional[Camera] = camera
        self.serial_device: Optional[SerialDevice] = serial_device
        self.turn_table: Optional[TurnTable] = turn_table
        self.camera_crane: Optional[CameraCrane] = camera_crane

        self.v_steps = settings.process.v_steps
        self.h_steps = settings.process.h_steps

        self.position_array: list[float] = []
        self.delta_rotation: float = 0

        self.generate_movesets()

        super().__init__()

    def generate_movesets(self):
        self.position_array = []
        self.delta_rotation = 360/self.v_steps

        stepsize = 1 / (self.h_steps - 1)

        for i in range(self.h_steps):
            self.position_array.append(i * stepsize)

    def generate_project(self) -> Project:
        pass

    def start_project(self, project: Project):
        if self.current_project is not None and self.project_running.is_set():
            return

        self.current_project = project
        self.project_paused.clear()
        self.project_running.set()

        self.current_x = 0
        self.current_y = 0
        self.is_bottom = False
        self.can_turn = False

        self.v_steps = settings.process.v_steps
        self.h_steps = settings.process.h_steps

        self.generate_movesets()

    def pause_project(self):
        if not self.current_project or not self.project_running.is_set():
            return

        self.project_paused.set()

    def resume_project(self):
        if not self.current_project or not self.project_running.is_set():
            return

        self.project_paused.clear()

    def stop_project(self):
        if not self.current_project:
            return

        self.project_running.clear()
        self.project_paused.clear()

    def all_ready(self):
        return self.crane_ready() and self.table_ready() and self.cluster_shot()

    def crane_ready(self):
        return not (self.camera_crane.is_moving or self.camera_crane.is_nulling)
    
    def table_ready(self):
        return not (self.turn_table.is_rotating or self.turn_table.is_nulling)
    
    def cluster_shot(self):
        return self.current_cluster.state.shot.is_set()

    def run(self):
        while not self.is_stopped():
            self._pause_event.wait()

            time.sleep(1/settings.app.thread_refreshrate)

            if not self.current_project:
                continue

            if not self.camera or not self.camera_crane or not self.turn_table or not self.serial_device:
                continue

            if not self.camera.is_connected() or not self.serial_device.is_connected():
                continue

            if not self.project_running.is_set():
                continue

            if self.project_paused.is_set():
                continue

            if self.current_y == (self.v_steps - 1):
                self.is_bottom = True
                self.can_turn = True
                self.pause()
                # hier aufforderung zum drehen zeigen

            if not self.all_ready():
                continue

            self.camera_crane.move_to(self.position_array[self.current_y])
            
            self.camera.enqueue_cluster(self.current_cluster)
            

            # move to x and y



