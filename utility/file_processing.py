import logging
from typing import Optional
from pathlib import Path
import shutil

import cv2
import numpy as np

logger = logging.getLogger(__name__)

# Allgemeine Funktionen zum Speichern, Laden, Bearbeiten von Bildern und Dateien.
# ! dst uns src werden nicht durch resolve_path verändert, da sie von der aufrufenden Funktion bereits korrekt aufgelöst sein sollten !

def save_image_buffer(img: np.ndarray, dst: str | Path) -> Path | None:
    """
    Speichert ein Bild als Datei.

    Args:
        img: Bild als numpy ndarray
        dst: Zielpfad der Datei

    Returns:
        Path zur gespeicherten Datei oder None bei Fehler
    """
    try:
        if img is None or not isinstance(img, np.ndarray) or img.size == 0:
            logger.debug(f"save_image_buffer: Ungültiges Bild (None oder leer)")
            return None

        destination = Path(dst)
        try:
            destination.parent.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            logger.error(
                f"save_image_buffer: Verzeichnis erstellen fehlgeschlagen | "
                f"Pfad: {destination.parent} | Fehler: {e}"
            )
            return None

        if not cv2.imwrite(str(destination), img):
            logger.error(
                f"save_image_buffer: cv2.imwrite fehlgeschlagen | "
                f"Ziel: {destination} | Bildgröße: {img.shape} | Datentyp: {img.dtype}"
            )
            return None

        return destination
    except OSError as e:
        logger.error(
            f"save_image_buffer: Dateisystem-Fehler | Ziel: {dst} | "
            f"Fehler: {e.strerror if hasattr(e, 'strerror') else str(e)}"
        )
        return None
    except Exception as e:
        logger.exception(
            f"save_image_buffer: Unerwarteter Fehler | Ziel: {dst} | Bildgröße: {img.shape if img is not None else 'N/A'}",
            exc_info=True
        )
        return None


def save_bytes(data: bytes, dst: str | Path) -> Path | None:
    """
    Speichert Binärdaten als Datei.

    Args:
        data: Daten als bytes
        dst: Zielpfad der Datei

    Returns:
        Path zur gespeicherten Datei oder None bei Fehler
    """
    try:
        if not isinstance(data, (bytes, bytearray)) or len(data) == 0:
            logger.debug(f"save_bytes: Ungültige Daten (leer oder falscher Typ)")
            return None

        destination = Path(dst)
        try:
            destination.parent.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            logger.error(
                f"save_bytes: Verzeichnis erstellen fehlgeschlagen | "
                f"Pfad: {destination.parent} | Fehler: {e}"
            )
            return None

        destination.write_bytes(data)
        return destination
    except OSError as e:
        logger.error(
            f"save_bytes: Dateisystem-Fehler | Ziel: {dst} | "
            f"Dateigröße: {len(data)} bytes | Fehler: {e.strerror if hasattr(e, 'strerror') else str(e)}"
        )
        return None
    except Exception as e:
        logger.exception(
            f"save_bytes: Unerwarteter Fehler | Ziel: {dst} | Dateigröße: {len(data) if isinstance(data, (bytes, bytearray)) else 'N/A'} bytes",
            exc_info=True
        )
        return None


def load_image_buffer(src: str | Path) -> Optional[np.ndarray]:
    """
    Lädt ein Bild aus einer Datei.

    Args:
        src: Pfad zur Bilddatei

    Returns:
        Bild als numpy ndarray oder None bei Fehler
    """
    try:
        source = Path(src)

        if not source.exists():
            logger.warning(f"load_image_buffer: Bilddatei nicht gefunden | Pfad: {source}")
            return None

        if not source.is_file():
            logger.warning(f"load_image_buffer: Pfad ist keine Datei | Pfad: {source}")
            return None

        if not source.suffix.lower() in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif']:
            logger.warning(f"load_image_buffer: Nicht unterstütztes Dateiformat | Datei: {source.suffix}")
            return None

        img = cv2.imread(str(source), cv2.IMREAD_COLOR)

        if img is None:
            logger.error(
                f"load_image_buffer: cv2.imread fehlgeschlagen | "
                f"Datei: {source} | Dateigröße: {source.stat().st_size} bytes"
            )
            return None

        return img
    except OSError as e:
        logger.error(
            f"load_image_buffer: Dateisystem-Fehler | Quelle: {src} | "
            f"Fehler: {e.strerror if hasattr(e, 'strerror') else str(e)}"
        )
        return None
    except Exception as e:
        logger.exception(
            f"load_image_buffer: Unerwarteter Fehler | Quelle: {src}",
            exc_info=True
        )
        return None


def delete_path(path: str | Path) -> bool:
    """
    Löscht eine Datei oder ein Verzeichnis.

    Args:
        path: Pfad zur Datei oder zum Verzeichnis

    Returns:
        True bei Erfolg oder wenn Pfad nicht existiert, sonst False
    """
    try:
        target = Path(path)

        if not target.exists():
            logger.debug(f"delete_path: Pfad existiert nicht, ignoriert | Pfad: {target}")
            return True

        if target.is_file():
            target.unlink()
            logger.debug(f"delete_path: Datei gelöscht | Datei: {target}")
        elif target.is_dir():
            shutil.rmtree(target)
            logger.debug(f"delete_path: Verzeichnis gelöscht | Verzeichnis: {target}")

        return True
    except PermissionError as e:
        logger.error(
            f"delete_path: Keine Berechtigung | Pfad: {path} | "
            f"Fehler: Unzureichende Schreibrechte"
        )
        return False
    except OSError as e:
        logger.error(
            f"delete_path: Dateisystem-Fehler | Pfad: {path} | "
            f"Fehler: {e.strerror if hasattr(e, 'strerror') else str(e)}"
        )
        return False
    except Exception as e:
        logger.exception(
            f"delete_path: Unerwarteter Fehler | Pfad: {path}",
            exc_info=True
        )
        return False


def move_file(src: str | Path, dst: str | Path, overwrite: bool = True) -> Path | None:
    """
    Verschiebt eine Datei an einen neuen Speicherort.

    Args:
        src: Quellpfad der Datei
        dst: Zielpfad der Datei
        overwrite: Existierende Datei überschreiben

    Returns:
        Path zur Zieldatei oder None bei Fehler
    """
    try:
        source = Path(src)
        destination = Path(dst)

        if not source.exists():
            logger.warning(f"move_file: Quelldatei nicht gefunden | Quelle: {source}")
            return None
        
        if not source.is_file():
            logger.warning(f"move_file: Quelle ist keine Datei | Quelle: {source}")
            return None

        try:
            destination.parent.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            logger.error(
                f"move_file: Zielverzeichnis erstellen fehlgeschlagen | "
                f"Ziel: {destination.parent} | Fehler: {e}"
            )
            return None

        if destination.exists():
            if not overwrite:
                logger.warning(
                    f"move_file: Zieldatei existiert, überschreiben deaktiviert | "
                    f"Ziel: {destination}"
                )
                return None
            try:
                destination.unlink()
            except OSError as e:
                logger.error(
                    f"move_file: Alte Zieldatei konnte nicht gelöscht werden | "
                    f"Ziel: {destination} | Fehler: {e}"
                )
                return None

        shutil.move(str(source), str(destination))
        logger.debug(f"move_file: Datei erfolgreich verschoben | Von: {source} | Zu: {destination}")
        return destination
    except PermissionError as e:
        logger.error(
            f"move_file: Keine Berechtigung | Von: {src} | Zu: {dst} | "
            f"Fehler: Unzureichende Schreibrechte"
        )
        return None
    except OSError as e:
        logger.error(
            f"move_file: Dateisystem-Fehler | Von: {src} | Zu: {dst} | "
            f"Fehler: {e.strerror if hasattr(e, 'strerror') else str(e)}"
        )
        return None
    except Exception as e:
        logger.exception(
            f"move_file: Unerwarteter Fehler | Von: {src} | Zu: {dst}",
            exc_info=True
        )
        return None


def flip_image_buffer(img: np.ndarray) -> Optional[np.ndarray]:
    """
    Dreht ein Bild um 180 Grad.

    Args:
        img: Bild als numpy ndarray

    Returns:
        Bild als numpy ndarray oder None bei Fehler
    """
    try:
        if img is None or not isinstance(img, np.ndarray) or img.size == 0:
            logger.debug(f"flip_image_buffer: Ungültiges Bild (None oder leer)")
            return None

        return cv2.rotate(img, cv2.ROTATE_180)
    except Exception as e:
        logger.exception(
            f"flip_image_buffer: Fehler | Bildgröße: {img.shape if img is not None else 'N/A'} | Datentyp: {img.dtype if img is not None else 'N/A'}",
            exc_info=True
        )
        return None


def downsample_image(img: np.ndarray, max_width: int = 1280, max_height: int = 720) -> Optional[np.ndarray]:
    """
    Skaliert ein Bild auf maximale Abmessungen.

    Behält das Seitenverhältnis bei.

    Args:
        img: Bild als numpy ndarray
        max_width: Maximale Breite in Pixeln
        max_height: Maximale Höhe in Pixeln

    Returns:
        Bild als numpy ndarray oder None bei Fehler
    """
    try:
        if img is None or not isinstance(img, np.ndarray) or img.size == 0:
            logger.debug(f"downsample_image: Ungültiges Bild (None oder leer)")
            return None

        h, w = img.shape[:2]
        if max_width <= 0 or max_height <= 0:
            logger.warning(
                f"downsample_image: Ungültige Zieldimensionen | max_width: {max_width} | max_height: {max_height}"
            )
            return None

        scale = min(max_width / w, max_height / h)

        if scale >= 1:
            logger.debug(f"downsample_image: Bild bereits kleiner als Zieldimension, keine Skalierung")
            return img.copy()

        new_w = max(1, int(w * scale))
        new_h = max(1, int(h * scale))
        logger.debug(f"downsample_image: Skaliere {w}x{h} -> {new_w}x{new_h}")

        resized = cv2.resize(
            img,
            (new_w, new_h),
            interpolation=cv2.INTER_AREA
        )

        return resized

    except Exception as e:
        logger.exception(
            f"downsample_image: Fehler | Original: {img.shape if img is not None else 'N/A'} | Ziel: {max_width}x{max_height}",
            exc_info=True
        )
        return None


def crop_image_buffer(img: np.ndarray, crop_ratio: float) -> Optional[np.ndarray]:
    """
    Schneidet ein Bild symmetrisch zu.

    Args:
        img: Bild als numpy ndarray
        crop_ratio: Zuschneide-Verhältnis von 0.0 bis 1.0

    Returns:
        Bild als numpy ndarray oder None bei Fehler
    """
    try:
        if img is None or not isinstance(img, np.ndarray) or img.size == 0:
            logger.debug(f"crop_image_buffer: Ungültiges Bild (None oder leer)")
            return None

        if not (0 <= crop_ratio <= 1):
            logger.warning(
                f"crop_image_buffer: Ungültiges Verhältnis | crop_ratio: {crop_ratio} | Erwartet: 0.0-1.0"
            )
            return None

        height, width = img.shape[:2]
        crop_x = int((width * crop_ratio) / 2)
        crop_y = int((height * crop_ratio) / 2)

        left = crop_x
        top = crop_y
        right = width - crop_x
        bottom = height - crop_y

        if right <= left or bottom <= top:
            logger.error(
                f"crop_image_buffer: Crop-Verhältnis zu groß | Original: {width}x{height} | crop_ratio: {crop_ratio}"
            )
            return None

        logger.debug(f"crop_image_buffer: Croppt {width}x{height} mit Verhältnis {crop_ratio}")
        return img[top:bottom, left:right].copy()
    except Exception as e:
        logger.exception(
            f"crop_image_buffer: Fehler | Bildgröße: {img.shape if img is not None else 'N/A'} | crop_ratio: {crop_ratio}",
            exc_info=True
        )
        return None