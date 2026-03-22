from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import io

from PIL import Image as PILImage
import numpy as np
import cv2 as cv
from PySide6.QtGui import QPixmap

from application.settings import settings
from application.file_processing import (
    crop_image_buffer,
    flip_image_buffer,
    save_bytes,
    save_preview_buffer,
    delete_file,
)


@dataclass
class Image:
    data: bytes = b""

    preview_dst: Optional[Path] = None
    dst: Optional[Path] = None

    def get_cv2_image(self) -> Optional[np.ndarray]:
        try:
            arr = np.frombuffer(self.data, dtype=np.uint8)
            return cv.imdecode(arr, cv.IMREAD_COLOR)
        except:
            return None
    
    def get_pil_image(self) -> Optional[PILImage.Image]:
        try:
            return PILImage.open(io.BytesIO(self.data))
        except:
            return None

    def get_pixmap(self) -> Optional[QPixmap]:
        try:
            pixmap = QPixmap()
            if pixmap.loadFromData(self.data):
                return pixmap
            return None
        except:
            return None
        
    def pil_to_data(self, img: PILImage.Image):
        try:
            buffer = io.BytesIO()
            img.save(buffer, format="JPEG")
            self.data = buffer.getvalue()
        except:
            pass

    def cv2_to_data(self, img: np.ndarray):
        try:
            success, encoded = cv.imencode(".jpg", img)
            if success:
                self.data = encoded.tobytes()
        except:
            pass

    def crop(self, value: float):
        try:
            img = self.get_cv2_image()
            if img is None:
                return

            cropped = crop_image_buffer(img, value)
            if cropped is None:
                return

            self.cv2_to_data(cropped)
        except:
            pass

    def flip(self):
        try:
            img = self.get_cv2_image()
            if img is None:
                return

            flipped = flip_image_buffer(img)
            if flipped is None:
                return

            self.cv2_to_data(flipped)
        except:
            pass

    def save_as_file(self, destination: Path):
        try:
            destination = Path(destination)

            if self.dst is not None and self.dst != destination:
                delete_file(self.dst)

            saved = save_bytes(self.data, destination)
            if saved is not None:
                self.dst = saved
        except:
            pass

    def save_preview(self, destination: Path):
        try:
            img = self.get_cv2_image()
            if img is None:
                return

            destination = Path(destination)

            if self.preview_dst is not None and self.preview_dst != destination:
                delete_file(self.preview_dst)

            saved = save_preview_buffer(
                img,
                destination,
                max_dim=settings.process.preview_dim,
                max_kb=settings.process.max_preview_kb,
            )

            if saved is not None:
                self.preview_dst = saved
        except:
            pass