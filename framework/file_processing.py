from typing import * 
from pathlib import Path
from PIL import Image
import shutil

import cv2
import numpy as np

def move_image(src: str|Path, dst: str|Path) -> Path:
    try:
        source = Path(src)
        
        if not source.exists():
            return False
        
        destination = Path(dst)
        
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(source, destination)
        
        return destination
    except:
        return source
    
def flip_image(src: str|Path, dst: str|Path = "") -> bool:
    try:
        if not Path(src).exists():
            return False
        
        Image.open(src).transpose(Image.ROTATE_180).save(dst if len(str(dst)) > 0 else src)
        
        return True
    except:
        return False
    
def crop_image(src: str | Path, val: float, dst: str | Path = "") -> bool:
    try:
        source = Path(src)
        if not source.exists():
            return False
        
        if not (0 <= val <= 1):
            return False
        
        img = Image.open(source)
        width, height = img.size

        crop_x = int((width * val) / 2)
        crop_y = int((height * val) / 2)

        left = crop_x
        top = crop_y
        right = width - crop_x
        bottom = height - crop_y

        if right <= left or bottom <= top:
            return False

        cropped = img.crop((left, top, right, bottom))

        output_path = dst if len(str(dst)) > 0 else source
        cropped.save(output_path)

        return True
    except:
        return False
    
def hdr_merge_mertens(src: List[str|Path], dst: str|Path, contrast: float = 1.0, exposure: float = 1.0, saturation: float = 1.0) -> bool:
    images = []
    
    for image_path in src:
        if not Path(image_path).exists():
            return False
                
        img = cv2.imread(image_path)
        
        if img is None:
            return False
        
        images.append(img)

    if len(images) < 2:
        return False
    
    merge_mertens = cv2.createMergeMertens(
        contrast_weight=contrast,
        exposure_weight=exposure,
        saturation_weight=saturation
    )
    
    res_mertens = merge_mertens.process(images)
    res_mertens_8bit = np.clip(res_mertens * 255, 0, 255).astype("uint8")
    
    cv2.imwrite(dst, res_mertens_8bit)
    
    return True
    
def hdr_merge_robertson(src: List[str|Path], dst: str|Path, exposure_times: List[float], gamma: float = 2.2) -> bool: # nochmals anschauen
    images = []
    
    for image_path in src:
        if not Path(image_path).exists():
            return False
                
        img = cv2.imread(image_path)
        
        if img is None:
            return False
        
        images.append(img)

    if len(images) < 2:
        return False
    
    exposure_times = np.array(exposure_times, dtype=np.float32)

    calibrate = cv2.createCalibrateRobertson(max_iter=10)
    response = calibrate.process(images, exposure_times)

    merge = cv2.createMergeRobertson()
    hdr = merge.process(images, exposure_times, response)

    tonemap = cv2.createTonemap(gamma=gamma)
    ldr = tonemap.process(hdr)

    ldr_8bit = np.clip(ldr * 255, 0, 255).astype("uint8")
    cv2.imwrite(dst, ldr_8bit)
    
    return True


# TODO: oberen teil refactoren


from typing import Optional, Sequence
from pathlib import Path

import cv2
import numpy as np

from PySide6.QtGui import QPixmap, QImage


def save_image_buffer(img: np.ndarray, dst: str | Path) -> Path | None:
    try:
        if img is None or not isinstance(img, np.ndarray) or img.size == 0:
            return None

        destination = Path(dst)
        destination.parent.mkdir(parents=True, exist_ok=True)

        if not cv2.imwrite(str(destination), img):
            return None

        return destination
    except:
        return None


def load_image_buffer(src: str | Path) -> Optional[np.ndarray]:
    try:
        source = Path(src)

        if not source.exists():
            return None

        img = cv2.imread(str(source), cv2.IMREAD_COLOR)

        if img is None:
            return None

        return img
    except:
        return None


def flip_image_buffer(img: np.ndarray) -> Optional[np.ndarray]:
    try:
        if img is None or not isinstance(img, np.ndarray) or img.size == 0:
            return None

        return cv2.rotate(img, cv2.ROTATE_180)
    except:
        return None


def crop_image_buffer(img: np.ndarray, val: float) -> Optional[np.ndarray]:
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
    except:
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
    except:
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
    except:
        return None
    
def cv_image_to_qpixmap(img: np.ndarray) -> QPixmap:
    """
    Erwartet OpenCV-Bild in BGR.
    """
    if img is None:
        return QPixmap()

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

def jpeg_buffer_to_qpixmap(buffer: bytes) -> QPixmap:
    pixmap = QPixmap()
    pixmap.loadFromData(buffer, "JPG")
    return pixmap