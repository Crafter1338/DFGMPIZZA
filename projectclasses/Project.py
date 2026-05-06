from dataclasses import dataclass, field
import time
from core.classes.camera import Camera
from projectclasses.ScanPosition import ScanPosition
from pathlib import Path

from application.process_logic import create_image_payloads
from utility.paths import resolve_path
from utility.settings import settings

@dataclass
class Project:
    article_number: str
    dir_destination: Path
    
    camera: Camera
    
    n_finished_scan_positions: int = 0
    n_total_scan_positions: int = 0
    
    scan_positions: list[ScanPosition] = field(default_factory=list)
    
    turnable: bool = False
    turn_confirmed: bool = False
    
    finished: bool = False
    finish_confirmed: bool = False
    
    index_current: int = 0
    index_turn: int = 0
    
    started_at: float = 0.0
    paused_at: float = 0.0
    resumed_at: float = 0.0
    
    total_pause_duration: float = 0.0
    estimated_time_remaining: float = 0.0
    
    paused: bool = False
    running: bool = False
    
    def calculate_estimated_time_remaining(self):
        if self.n_finished_scan_positions == 0:
            return
        
        elapsed_time = time.time() - self.started_at

        if self.paused_at and not self.resumed_at:
            elapsed_time -= time.time() - self.paused_at

        elapsed_time -= self.total_pause_duration
        
        time_per_position = elapsed_time / self.n_finished_scan_positions
        self.estimated_time_remaining = time_per_position * (self.n_total_scan_positions - self.n_finished_scan_positions)
    
    def start(self):
        self.started_at = time.time()
        self.running = True
        self.paused = False
    
    def pause(self):
        if not self.paused_at:
            self.paused_at = time.time()
            self.resumed_at = 0.0
            
        self.running = False
        self.paused = True
            
        self.calculate_estimated_time_remaining()

    def resume(self):
        if self.paused_at:
            self.resumed_at = time.time()
            self.total_pause_duration += self.resumed_at - self.paused_at
            self.paused_at = 0.0
            self.resumed_at = 0.0
            
        self.paused = False
        self.running = True
            
        self.calculate_estimated_time_remaining()
    
    def stop(self):
        self.initialize()
    
    def generate_scan_positions(self):
        h_steps = max(2, int(settings.process.h_steps))
        v_steps = max(2, int(settings.process.v_steps)) 

        if v_steps % 2 == 1:
            v_steps += 1
            
        for v_indx in range(v_steps):
            y = 1 - 2 * (v_indx / (v_steps - 1))

            flipped = y < 0
            y_pos = abs(y)
            
            for h_indx in range(h_steps):
                x_pos = (h_indx / (h_steps - 1)) * 360
                
                self.scan_positions.append(ScanPosition(
                        image_payloads=create_image_payloads(self.camera),
                        x_pos=x_pos,
                        y_pos=y_pos,

                        x_name=str(h_indx + 1),
                        y_name=str(v_indx + 1),

                        flipped=flipped,
                    ))
                
        self.index_turn = next(
            v_indx for v_indx in range(v_steps)
            if (1 - 2 * (v_indx / (v_steps - 1))) < 0
        ) * h_steps
        
        self.n_total_scan_positions = len(self.scan_positions)
                
    
    def initialize(self):
        resolve_path(self.dir_destination).mkdir(parents=True, exist_ok=True) # Projektordner erstellen
        
        if settings.process.create_previews:
            (resolve_path(self.dir_destination) / "preview").mkdir(parents=True, exist_ok=True) # Previewordner erstellen
            
        self.n_finished_scan_positions = 0
        self.n_total_scan_positions = 0
        
        self.scan_positions = []
        
        self.turnable = False
        self.turn_confirmed = False
        
        self.finished = False
        self.finish_confirmed = False
        
        self.index_current = 0
        self.index_turn = 0
        
        self.started_at = time.time()
        self.paused_at = 0.0
        self.resumed_at = 0.0
        
        self.estimated_time_remaining = 0.0
        
        self.running = False
        self.paused = False
        
        self.generate_scan_positions()
    
    def __post_init__(self):
        self.dir_destination = Path(self.dir_destination) / self.article_number
         
        self.initialize()
        
    