import importlib.util
import sys
import time
import unittest
from concurrent.futures import Future
from types import ModuleType, SimpleNamespace
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

for module_name in ("edsdk", "pythoncom"):
    sys.modules.setdefault(module_name, ModuleType(module_name))

serial_module = sys.modules.setdefault("serial", ModuleType("serial"))
serial_module.__path__ = []
serial_module.SerialException = Exception
class _Serial:
    def __init__(self, *args, **kwargs):
        self.is_open = True
    def close(self):
        self.is_open = False
    def write(self, data):
        pass
    def flush(self):
        pass
    def read(self, size):
        return b""
serial_module.Serial = _Serial

serial_tools_module = sys.modules.setdefault("serial.tools", ModuleType("serial.tools"))
serial_tools_module.__path__ = []
serial_list_ports_module = sys.modules.setdefault("serial.tools.list_ports", ModuleType("serial.tools.list_ports"))
serial_list_ports_module.comports = lambda: []
serial_tools_module.list_ports = serial_list_ports_module
serial_module.tools = serial_tools_module

import numpy as np
if importlib.util.find_spec("cv2") is None:
    cv2_module = sys.modules.setdefault("cv2", ModuleType("cv2"))
    cv2_module.IMREAD_COLOR = 1
    cv2_module.IMWRITE_JPEG_QUALITY = 1
    cv2_module.imdecode = lambda *args, **kwargs: np.zeros((1, 1, 3), dtype=np.uint8)
    cv2_module.imencode = lambda *args, **kwargs: (True, np.zeros((1,), dtype=np.uint8))
    cv2_module.resize = lambda img, size, interpolation=None: img
    cv2_module.imwrite = lambda path, img: True
    cv2_module.createMergeDebevec = lambda: SimpleNamespace(process=lambda imgs, exp: imgs[0])
    cv2_module.createTonemapDrago = lambda gamma, saturation, bias: SimpleNamespace(process=lambda hdr: hdr)
    cv2_module.imread = lambda *args, **kwargs: np.zeros((1, 1, 3), dtype=np.uint8)
    sys.modules["cv2"] = cv2_module

if importlib.util.find_spec("PySide6") is None:
    pyside6_module = sys.modules.setdefault("PySide6", ModuleType("PySide6"))
    qtgui_module = sys.modules.setdefault("PySide6.QtGui", ModuleType("PySide6.QtGui"))
    class QPixmap:
        def __init__(self):
            pass
        def loadFromData(self, data):
            return False
    class QImage:
        def __init__(self, *args, **kwargs):
            pass
    qtgui_module.QPixmap = QPixmap
    qtgui_module.QImage = QImage
    pyside6_module.QtGui = qtgui_module
    sys.modules["PySide6"] = pyside6_module
    sys.modules["PySide6.QtGui"] = qtgui_module

if importlib.util.find_spec("utility.file_processing") is None:
    file_processing_module = sys.modules.setdefault("utility.file_processing", ModuleType("utility.file_processing"))
    file_processing_module.crop_image_buffer = lambda img, value: img
    file_processing_module.flip_image_buffer = lambda img, value: img
    def _save_bytes(data, dst):
        destination = Path(dst)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
        return destination
    file_processing_module.save_bytes = _save_bytes
    file_processing_module.delete_path = lambda path: True
    file_processing_module.downsample_image = lambda img: img

if importlib.util.find_spec("utility.image_processing") is None:
    image_processing_module = sys.modules.setdefault("utility.image_processing", ModuleType("utility.image_processing"))
    def _save_preview_buffer(img, dst, **kwargs):
        destination = Path(dst)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(b"")
        return destination
    def _hdr_merge_drago_buffer(images, exposure_times, gamma=1.5, saturation=1.0, bias=0.85):
        return images[0] if images else None
    image_processing_module.save_preview_buffer = _save_preview_buffer
    image_processing_module.hdr_merge_drago_buffer = _hdr_merge_drago_buffer

from core.classes.process_orchestrator import ProcessOrchestrator
from projectclasses.Project import Project
from projectclasses.ScanPosition import ScanPosition
from projectclasses.ShotPayload import ShotPayload
from utility.settings import settings


class DummyCamera:
    def __init__(self):
        self.iso_names = [0, 100, 125, 160, 200, 250, 320, 400]
        self.av_names = [5.6, 8, 11, 16, 22]
        self.tv_names = [30, 15, 8, 4, 2, 1, 0.5]
        self._connected = True

    def is_connected(self):
        return self._connected

    def enqueue_shot(self, payload: ShotPayload):
        future = Future()
        future.set_result(SimpleNamespace(success=True, data=b"JPEGDATA"))
        return future


class DummySerialOrchestrator:
    def __init__(self):
        self._connected = True
        self.is_set_up = True

    def is_connected(self):
        return True

    def queue_instructions(self, instructions):
        future = Future()
        future.set_result(None)
        return future


class DummyTurnTable:
    def __init__(self):
        self.nulled = type("Evt", (), {"is_set": lambda self: True})()
        self.rotated = type("Evt", (), {"wait": lambda self, timeout=None: None})()
        self.is_nulling = False

    def rotate_by(self, delta):
        pass


class DummyCameraCrane:
    def __init__(self):
        self.nulled = type("Evt", (), {"is_set": lambda self: True})()
        self.moved = type("Evt", (), {"is_set": lambda self: True})()

    def move_to(self, pos):
        pass


class ProcessFlowTest(unittest.TestCase):
    def test_process_orchestrator_advances_scan_position_and_finishes(self):
        camera = DummyCamera()
        serial_orchestrator = DummySerialOrchestrator()
        crane = DummyCameraCrane()
        turntable = DummyTurnTable()

        orchestrator = ProcessOrchestrator(camera, serial_orchestrator, crane, turntable)

        with TemporaryDirectory() as tmp_dir:
            project = Project("TESTARTICLE", Path(tmp_dir), camera)

            project.scan_positions = [
                ScanPosition(
                    x_pos=0.0,
                    y_pos=0.0,
                    x_name="1",
                    y_name="1",
                    flipped=False,
                    image_payloads=[ShotPayload(iso=settings.camera.iso, av=settings.camera.av, tv=settings.camera.base_tv)],
                )
            ]
            project.n_total_scan_positions = 1
            project.index_turn = -1
            project.index_current = 0
            project.running = True
            project.paused = False
            project.finished = False
            project.turnable = False
            project.turn_confirmed = True

            def finish_noop(_):
                project.scan_positions[0].finished = True

            project.scan_positions[0].finish = finish_noop
            orchestrator.set_project(project)

            orchestrator.loop()

            deadline = time.time() + 1.0
            while not project.scan_positions[0].finished and time.time() < deadline:
                time.sleep(0.01)

            self.assertEqual(project.index_current, 1)
            self.assertEqual(project.n_finished_scan_positions, 1)
            self.assertTrue(project.scan_positions[0].finished)

            orchestrator.loop()

            self.assertTrue(project.finished)
            self.assertFalse(project.running)


if __name__ == "__main__":
    unittest.main()
