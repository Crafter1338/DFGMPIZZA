from typing import Optional, Sequence
from pathlib import Path
import shutil
import logging
import traceback

import cv2
import numpy as np
from PySide6.QtGui import QPixmap, QImage

logger = logging.getLogger(__name__)

def save_image_buffer(img: np.ndarray, dst: str | Path) -> Path | None:
    """
    Speichert das Bild (cv2 img, ndarray) in dst
    """
    try:
        if img is None or not isinstance(img, np.ndarray) or img.size == 0:
            return None

        destination = Path(dst)
        destination.parent.mkdir(parents=True, exist_ok=True)

        if not cv2.imwrite(str(destination), img):
            return None

        return destination
    except Exception as e:
        logger.exception("save_image_buffer error")
        return None


def save_bytes(data: bytes, dst: str | Path) -> Path | None:
    """
    Speichert das Bild (bytes) in dst
    """
    try:
        if not isinstance(data, (bytes, bytearray)) or len(data) == 0:
            return None

        destination = Path(dst)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)

        return destination
    except Exception as e:
        logger.exception("save_bytes error")
        return None


def load_image_buffer(src: str | Path) -> Optional[np.ndarray]:
    """
    Lädt src zu cv2 Bild
    """
    try:
        source = Path(src)

        if not source.exists():
            return None

        img = cv2.imread(str(source), cv2.IMREAD_COLOR)

        if img is None:
            return None

        return img
    except Exception as e:
        logger.exception("load_image_buffer error")
        return None


def delete_file(path: str | Path) -> bool:
    """
    Löscht Datei bei path
    """
    try:
        target = Path(path)

        if not target.exists():
            return True

        if not target.is_file():
            return False

        target.unlink()
        return True
    except Exception as e:
        logger.exception("delete_file error")
        return False


def move_file(src: str | Path, dst: str | Path, overwrite: bool = True) -> Path | None:
    """
    Bewegt Datei von src nach dst
    """
    try:
        source = Path(src)
        destination = Path(dst)

        if not source.exists() or not source.is_file():
            return None

        destination.parent.mkdir(parents=True, exist_ok=True)

        if destination.exists():
            if not overwrite:
                return None
            destination.unlink()

        shutil.move(str(source), str(destination))
        return destination
    except Exception as e:
        logger.exception("move_file error")
        return None


def flip_image_buffer(img: np.ndarray) -> Optional[np.ndarray]:
    """
    Dreht das Bild (cv2 img, ndarray) um 180°
    """
    try:
        if img is None or not isinstance(img, np.ndarray) or img.size == 0:
            return None

        return cv2.rotate(img, cv2.ROTATE_180)
    except Exception as e:
        logger.exception("flip_image_buffer error")
        return None


def downsample_to_hd(img: np.ndarray) -> Optional[np.ndarray]:
    """
    Skaliert ein Bild auf maximal 1280x720 (HD), behält Seitenverhältnis bei.
    """
    try:
        if img is None or not isinstance(img, np.ndarray) or img.size == 0:
            return None

        target_w, target_h = 1280, 720
        h, w = img.shape[:2]

        scale = min(target_w / w, target_h / h)

        if scale >= 1:
            return img.copy()

        new_w = max(1, int(w * scale))
        new_h = max(1, int(h * scale))

        resized = cv2.resize(
            img,
            (new_w, new_h),
            interpolation=cv2.INTER_AREA  # ideal für Downsampling (laut ChatGPT)
        )

        return resized

    except Exception:
        logger.exception("downsample_to_hd error")
        return None


def crop_image_buffer(img: np.ndarray, val: float) -> Optional[np.ndarray]:
    """
    Cropt das Bild (cv2 img, ndarray) mit crop
    """
    try:
        if img is None or not isinstance(img, np.ndarray) or img.size == 0:
            return None

        if not (0 <= val <= 1):
            return None

        height, width = img.shape[:2]

        crop_x = int((width * val) / 2)
        crop_y = int((height * val) / 2)

        left = crop_x
        top = crop_y
        right = width - crop_x
        bottom = height - crop_y

        if right <= left or bottom <= top:
            return None

        return img[top:bottom, left:right].copy()
    except Exception as e:
        logger.exception("crop_image_buffer error")
        return None


def save_preview_buffer(
    img: np.ndarray,
    dst: str | Path,
    max_dim: int = 1024,
    max_kb: int = 18,
    min_quality: int = 15,
    start_quality: int = 90,
    step: int = 5,
) -> Path | None:
    """
    Speichert das Bild (cv2 img, ndarray) als Preview nach Vorgaben in dst
    """
    try:
        if img is None or img.size == 0:
            return None

        destination = Path(dst)
        destination.parent.mkdir(parents=True, exist_ok=True)

        preview = img
        height, width = preview.shape[:2]
        longest_edge = max(width, height)

        if longest_edge > max_dim:
            scale = max_dim / longest_edge
            new_width = max(1, int(width * scale))
            new_height = max(1, int(height * scale))

            preview = cv2.resize(
                preview,
                (new_width, new_height),
                interpolation=cv2.INTER_AREA
            )

        max_bytes = max_kb * 1024
        best_encoded_under_limit = None
        smallest_encoded = None

        for quality in range(start_quality, min_quality - 1, -step):
            success, encoded = cv2.imencode(
                ".jpg",
                preview,
                [int(cv2.IMWRITE_JPEG_QUALITY), quality]
            )

            if not success:
                continue

            encoded_bytes = encoded.tobytes()

            if smallest_encoded is None or len(encoded_bytes) < len(smallest_encoded):
                smallest_encoded = encoded_bytes

            if len(encoded_bytes) <= max_bytes:
                best_encoded_under_limit = encoded_bytes
                break

        if best_encoded_under_limit is not None:
            destination.write_bytes(best_encoded_under_limit)
            return destination

        if smallest_encoded is not None:
            destination.write_bytes(smallest_encoded)
            return destination

        return None
    except Exception as e:
        logger.exception("save_preview_buffer error")
        return None


def hdr_merge_mertens_buffer(
    images: Sequence[np.ndarray],
    contrast: float = 1.0,
    exposure: float = 1.0,
    saturation: float = 1.0,
) -> Optional[np.ndarray]:
    try:
        valid_images: list[np.ndarray] = []

        for img in images:
            if img is None or not isinstance(img, np.ndarray) or img.size == 0:
                return None
            valid_images.append(img)

        if len(valid_images) < 2:
            return None

        merge_mertens = cv2.createMergeMertens(
            contrast_weight=contrast,
            exposure_weight=exposure,
            saturation_weight=saturation,
        )

        res_mertens = merge_mertens.process(valid_images)
        res_mertens_8bit = np.clip(res_mertens * 255, 0, 255).astype(np.uint8)

        return res_mertens_8bit
    except Exception as e:
        logger.exception("hdr_merge_mertens_buffer error")
        return None


def hdr_merge_robertson_buffer(
    images: Sequence[np.ndarray],
    exposure_times: Sequence[float],
    gamma: float = 2.2,
) -> Optional[np.ndarray]:
    try:
        valid_images: list[np.ndarray] = []

        for img in images:
            if img is None or not isinstance(img, np.ndarray) or img.size == 0:
                return None
            valid_images.append(img)

        if len(valid_images) < 2:
            return None

        if len(exposure_times) != len(valid_images):
            return None

        exposure_times_np = np.array(exposure_times, dtype=np.float32)

        calibrate = cv2.createCalibrateRobertson(max_iter=10)
        response = calibrate.process(valid_images, exposure_times_np)

        merge = cv2.createMergeRobertson()
        hdr = merge.process(valid_images, exposure_times_np, response)

        tonemap = cv2.createTonemap(gamma=gamma)
        ldr = tonemap.process(hdr)

        ldr_8bit = np.clip(ldr * 255, 0, 255).astype(np.uint8)

        return ldr_8bit
    except Exception as e:
        logger.exception("hdr_merge_robertson_buffer error")
        return None


def cv_image_to_qpixmap(img: np.ndarray) -> QPixmap:
    """
    Konvertiert ein cv2 img zu einer pyside6 QPixmap
    """
    try:
        if img is None or not isinstance(img, np.ndarray) or img.size == 0:
            return QPixmap()

        if len(img.shape) == 2:
            h, w = img.shape
            bytes_per_line = w
            qimg = QImage(
                img.data,
                w,
                h,
                bytes_per_line,
                QImage.Format.Format_Grayscale8
            ).copy()
            return QPixmap.fromImage(qimg)

        if len(img.shape) == 3 and img.shape[2] == 3:
            rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb.shape
            bytes_per_line = ch * w

            qimg = QImage(
                rgb.data,
                w,
                h,
                bytes_per_line,
                QImage.Format.Format_RGB888
            ).copy()

            return QPixmap.fromImage(qimg)

        if len(img.shape) == 3 and img.shape[2] == 4:
            rgba = cv2.cvtColor(img, cv2.COLOR_BGRA2RGBA)
            h, w, ch = rgba.shape
            bytes_per_line = ch * w

            qimg = QImage(
                rgba.data,
                w,
                h,
                bytes_per_line,
                QImage.Format.Format_RGBA8888
            ).copy()

            return QPixmap.fromImage(qimg)

        return QPixmap()
    except Exception as e:
        logger.exception("cv_image_to_qpixmap error")
        return QPixmap()


def jpeg_buffer_to_qpixmap(buffer: bytes) -> QPixmap:
    """
    Konvertiert bytes zu einer pyside6 QPixmap
    """
    try:
        pixmap = QPixmap()
        pixmap.loadFromData(buffer)
        return pixmap
    except Exception as e:
        logger.exception("jpeg_buffer_to_qpixmap error")
        return QPixmap()