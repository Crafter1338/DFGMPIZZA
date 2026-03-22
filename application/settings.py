from dataclasses import dataclass, asdict, field
import json
from pathlib import Path

@dataclass
class AppSettings:
    thread_refreshrate: int = 20
    reconnect_delay: float = 0.5
    image_crop: float = 0

##################################################################

@dataclass
class UISettings:
    refreshrate: int = 20
    preview_refreshrate: int = 15

##################################################################

@dataclass
class CameraSettings:
    reconnect_delay: float = 0.5
    timeout: float = 15
    liveview_refresh_rate: float = 4

    iso: int = 100
    av: float = 8
    base_tv: float = 0.5

    hdr_shot_count: int = 3
    hdr_ev: float = 1

    contrast_weight: float = 1
    exposure_weight: float = 1
    saturation_weight: float = 1

    tonemap_gamma: float = 2.2

    use_mertens: bool = True
    use_robertson: bool = False


##################################################################

@dataclass 
class ProcessSettings:
    destination_dir: str = "application/results"

    preview_dim: int = 1024
    max_preview_kb: int = 18
    create_previews: bool = True

    h_steps: int = 12
    v_steps: int = 12

##################################################################

@dataclass
class SerialSettings:
    port: str = "COM5"
    baudrate: int = 57600
    timeout: float = 0.25
    reconnect_delay: float = 0.5

@dataclass
class MechanicsSettings:
    settle_time: float = 0.3
    vertical_swing_compensation_delay: float = 6

@dataclass
class CameraCraneSettings:
    min_pos: float = 0.1
    max_pos: float = 0.9
    homing_duration: int = 50

@dataclass
class TurnTableSettings:
    test: int = 0

##################################################################

file = Path("application/settings.json")

def _merge(default: dict, loaded: dict):
    """Merge loaded dict into default dict recursively"""
    for k, v in default.items():
        if k in loaded:
            if isinstance(v, dict) and isinstance(loaded[k], dict):
                default[k] = _merge(v, loaded[k])
            else:
                default[k] = loaded[k]
    return default

@dataclass
class Settings:
    app: AppSettings = field(default_factory=AppSettings)
    ui: UISettings = field(default_factory=UISettings)
    camera: CameraSettings = field(default_factory=CameraSettings)
    process: ProcessSettings = field(default_factory=ProcessSettings)
    serial: SerialSettings = field(default_factory=SerialSettings)
    mechanics: MechanicsSettings = field(default_factory=MechanicsSettings)
    camera_crane: CameraCraneSettings = field(default_factory=CameraCraneSettings)
    turn_table: TurnTableSettings = field(default_factory=TurnTableSettings)

    def load(self):
        default = asdict(self)

        if file.exists():
            try:
                with open(file, "r", encoding="utf-8") as f:
                    loaded = json.load(f)

                default = _merge(default, loaded)

            except Exception:
                pass

        self.app = AppSettings(**default["app"])
        self.ui = UISettings(**default["ui"])
        self.camera = CameraSettings(**default["camera"])
        self.process = ProcessSettings(**default["process"])
        self.serial = SerialSettings(**default["serial"])
        self.mechanics = MechanicsSettings(**default["mechanics"])
        self.camera_crane = CameraCraneSettings(**default["camera_crane"])
        self.turn_table = TurnTableSettings(**default["turn_table"])

        self.save()
        return self

    def save(self):
        file.parent.mkdir(parents=True, exist_ok=True)

        with open(file, "w", encoding="utf-8") as f:
            json.dump(asdict(self), f, indent=4)

        return self

settings = Settings().load()