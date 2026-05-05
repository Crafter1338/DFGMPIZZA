import logging
from typing import Optional, Sequence
from pathlib import Path

import cv2
import numpy as np
from PySide6.QtGui import QPixmap, QImage

logger = logging.getLogger(__name__)

# Spezialisierte Funktionen für die Bildverarbeitung.
# ! dst uns src werden nicht durch resolve_path verändert, da sie von der aufrufenden Funktion bereits korrekt aufgelöst sein sollten !

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
    Speichert ein optimiertes Vorschaubild.

    Passt die JPEG-Qualität automatisch an, um die Dateigröße unter dem Limit zu halten.

    Args:
        img: Bild als numpy ndarray
        dst: Zielpfad der Datei
        max_dim: Maximale Bilddimension in Pixeln
        max_kb: Maximale Dateigröße in Kilobyte
        min_quality: Minimale JPEG-Qualität
        start_quality: Startwert für JPEG-Qualität
        step: Schrittweite zur Reduktion der Qualität

    Returns:
        Path zur gespeicherten Datei oder None bei Fehler
    """
    try:
        if img is None or img.size == 0:
            logger.debug(f"save_preview_buffer: Ungültiges Bild (None oder leer)")
            return None

        destination = Path(dst)
        try:
            destination.parent.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            logger.error(
                f"save_preview_buffer: Verzeichnis erstellen fehlgeschlagen | "
                f"Pfad: {destination.parent} | Fehler: {e}"
            )
            return None

        preview = img
        height, width = preview.shape[:2]
        longest_edge = max(width, height)
        logger.debug(f"save_preview_buffer: Original {width}x{height}")

        if longest_edge > max_dim:
            scale = max_dim / longest_edge
            new_width = max(1, int(width * scale))
            new_height = max(1, int(height * scale))
            logger.debug(f"save_preview_buffer: Skaliere auf {new_width}x{new_height}")

            preview = cv2.resize(
                preview,
                (new_width, new_height),
                interpolation=cv2.INTER_AREA
            )

        max_bytes = max_kb * 1024
        best_encoded_under_limit = None
        smallest_encoded = None
        best_quality = None
        smallest_size = None

        for quality in range(start_quality, min_quality - 1, -step):
            try:
                success, encoded = cv2.imencode(
                    ".jpg",
                    preview,
                    [int(cv2.IMWRITE_JPEG_QUALITY), quality]
                )
            except Exception as e:
                logger.warning(f"save_preview_buffer: JPEG-Kodierung bei Qualität {quality} fehlgeschlagen")
                continue

            if not success:
                logger.debug(f"save_preview_buffer: JPEG-Kodierung bei Qualität {quality} erfolglos")
                continue

            encoded_bytes = encoded.tobytes()
            current_size = len(encoded_bytes)

            if smallest_encoded is None or current_size < smallest_size:
                smallest_encoded = encoded_bytes
                smallest_size = current_size

            if current_size <= max_bytes:
                best_encoded_under_limit = encoded_bytes
                best_quality = quality
                logger.debug(f"save_preview_buffer: Qualität {quality} erfüllt Limit ({current_size}/{max_bytes} bytes)")
                break

        if best_encoded_under_limit is not None:
            try:
                destination.write_bytes(best_encoded_under_limit)
                logger.debug(f"save_preview_buffer: Datei gespeichert mit Qualität {best_quality} ({len(best_encoded_under_limit)} bytes)")
                return destination
            except OSError as e:
                logger.error(
                    f"save_preview_buffer: Datei schreiben fehlgeschlagen | Ziel: {destination} | Fehler: {e}"
                )
                return None

        if smallest_encoded is not None:
            logger.warning(
                f"save_preview_buffer: Limit von {max_kb}KB nicht erreichbar | "
                f"Beste Größe: {smallest_size} bytes | Speichere mit reduzierter Qualität"
            )
            try:
                destination.write_bytes(smallest_encoded)
                logger.debug(f"save_preview_buffer: Datei gespeichert mit kompromissierter Qualität ({smallest_size} bytes)")
                return destination
            except OSError as e:
                logger.error(
                    f"save_preview_buffer: Datei schreiben fehlgeschlagen | Ziel: {destination} | Fehler: {e}"
                )
                return None

        logger.error(
            f"save_preview_buffer: Keine gültige JPEG-Kodierung möglich | "
            f"Bildgröße: {preview.shape} | Datentyp: {preview.dtype}"
        )
        return None
    except OSError as e:
        logger.error(
            f"save_preview_buffer: Dateisystem-Fehler | Ziel: {dst} | "
            f"Fehler: {e.strerror if hasattr(e, 'strerror') else str(e)}"
        )
        return None
    except Exception as e:
        logger.exception(
            f"save_preview_buffer: Unerwarteter Fehler | Ziel: {dst} | "
            f"Bildgröße: {img.shape if img is not None else 'N/A'} | max_kb: {max_kb}",
            exc_info=True
        )
        return None
    

def hdr_merge_drago_buffer(
    images: Sequence[np.ndarray],
    exposure_times: Sequence[float],
    gamma: float = 1.5,
    saturation: float = 1.0,
    bias: float = 0.85,
) -> Optional[np.ndarray]:
    """
    Erstellt ein HDR-Bild aus mehreren Belichtungen.

    Führt mehrere Bilder mit unterschiedlichen Belichtungszeiten zusammen und wendet Tonemapping an.

    Args:
        images: Sequenz von Bildern als numpy ndarrays (gleiche Größe erforderlich)
        exposure_times: Belichtungszeiten in Sekunden
        gamma: Gamma-Wert für Tonemapping
        saturation: Farbsättigung für Tonemapping
        bias: Bias-Wert für Drago-Tonemapping

    Returns:
        Bild als numpy ndarray oder None bei Fehler
    """
    try:
        valid_images: list[np.ndarray] = []
        image_count = 0

        for idx, img in enumerate(images):
            image_count += 1
            if img is None or not isinstance(img, np.ndarray) or img.size == 0:
                logger.warning(f"hdr_merge_drago_buffer: Ungültiges Bild an Index {idx}")
                return None
            
            if idx > 0 and img.shape != valid_images[0].shape:
                logger.error(
                    f"hdr_merge_drago_buffer: Bildgrößen stimmen nicht überein | "
                    f"Bild 0: {valid_images[0].shape} | Bild {idx}: {img.shape}"
                )
                return None
            
            valid_images.append(img)

        if len(valid_images) < 2:
            logger.warning(
                f"hdr_merge_drago_buffer: Zu wenige Bilder | Erhalten: {image_count} | Erforderlich: 2"
            )
            return None

        if len(exposure_times) != len(valid_images):
            logger.error(
                f"hdr_merge_drago_buffer: Anzahl Bilder und Belichtungszeiten stimmen nicht überein | "
                f"Bilder: {len(valid_images)} | Belichtungszeiten: {len(exposure_times)}"
            )
            return None
        
        if any(t <= 0 for t in exposure_times):
            logger.warning(
                f"hdr_merge_drago_buffer: Ungültige Belichtungszeiten | Zeiten: {exposure_times}"
            )
            return None

        logger.debug(
            f"hdr_merge_drago_buffer: Starte HDR-Merge | Bilder: {len(valid_images)} | "
            f"Bildgröße: {valid_images[0].shape} | Belichtungszeiten: {exposure_times}"
        )

        exposure_times_np = np.array(exposure_times, dtype=np.float32)

        try:
            merge = cv2.createMergeDebevec()
            hdr = merge.process(valid_images, exposure_times_np)
        except Exception as e:
            logger.error(
                f"hdr_merge_drago_buffer: Debevec-Merge fehlgeschlagen | Fehler: {e}"
            )
            return None

        try:
            tonemap = cv2.createTonemapDrago(
                gamma=gamma,
                saturation=saturation,
                bias=bias,
            )
            ldr = tonemap.process(hdr)
        except Exception as e:
            logger.error(
                f"hdr_merge_drago_buffer: Drago-Tonemapping fehlgeschlagen | "
                f"gamma: {gamma} | saturation: {saturation} | bias: {bias} | Fehler: {e}"
            )
            return None

        ldr = np.clip(ldr, 0, 1)
        result = (ldr * 255).astype(np.uint8)
        logger.debug(f"hdr_merge_drago_buffer: HDR-Merge abgeschlossen | Ausgabe: {result.shape}")

        return result

    except Exception as e:
        logger.exception(
            f"hdr_merge_drago_buffer: Unerwarteter Fehler | Bilder: {len(images) if images else 0} | "
            f"Belichtungszeiten: {len(exposure_times) if exposure_times else 0}",
            exc_info=True
        )
        return None
    

def cv_image_to_qpixmap(img: np.ndarray) -> QPixmap:
    """
    Konvertiert ein Bild in eine QPixmap.

    Unterstützt Graustufen-, RGB- und RGBA-Bilder.

    Args:
        img: Bild als numpy ndarray

    Returns:
        QPixmap, bei ungültigem Input ein leeres QPixmap
    """
    try:
        if img is None or not isinstance(img, np.ndarray) or img.size == 0:
            logger.debug(f"cv_image_to_qpixmap: Ungültiges Bild (None, falscher Typ oder leer)")
            return QPixmap()

        if len(img.shape) == 2:
            h, w = img.shape
            logger.debug(f"cv_image_to_qpixmap: Konvertiere Graustufenbild ({w}x{h})")
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
            h, w, ch = img.shape
            logger.debug(f"cv_image_to_qpixmap: Konvertiere BGR-Bild ({w}x{h})")
            rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
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
            h, w, ch = img.shape
            logger.debug(f"cv_image_to_qpixmap: Konvertiere BGRA-Bild ({w}x{h})")
            rgba = cv2.cvtColor(img, cv2.COLOR_BGRA2RGBA)
            bytes_per_line = ch * w

            qimg = QImage(
                rgba.data,
                w,
                h,
                bytes_per_line,
                QImage.Format.Format_RGBA8888
            ).copy()

            return QPixmap.fromImage(qimg)

        logger.warning(
            f"cv_image_to_qpixmap: Nicht unterstütztes Bildformat | Shape: {img.shape} | Datentyp: {img.dtype}"
        )
        return QPixmap()
    except Exception as e:
        logger.exception(
            f"cv_image_to_qpixmap: Konvertierungsfehler | Bildgröße: {img.shape if img is not None else 'N/A'} | Datentyp: {img.dtype if img is not None else 'N/A'}",
            exc_info=True
        )
        return QPixmap()


def jpeg_buffer_to_qpixmap(buffer: bytes) -> QPixmap:
    """
    Konvertiert JPEG-Rohdaten in eine QPixmap.

    Args:
        buffer: JPEG-Daten als bytes

    Returns:
        QPixmap, bei ungültigen Daten ein leeres QPixmap
    """
    try:
        if not isinstance(buffer, (bytes, bytearray)) or len(buffer) == 0:
            logger.debug(f"jpeg_buffer_to_qpixmap: Ungültige Daten (leer oder falscher Typ)")
            return QPixmap()
        
        pixmap = QPixmap()
        if not pixmap.loadFromData(buffer):
            logger.warning(
                f"jpeg_buffer_to_qpixmap: JPEG-Daten konnten nicht geladen werden | "
                f"Dateigröße: {len(buffer)} bytes"
            )
            return QPixmap()
        
        logger.debug(f"jpeg_buffer_to_qpixmap: Datei erfolgreich geladen | Größe: {pixmap.size()}")
        return pixmap
    except Exception as e:
        logger.exception(
            f"jpeg_buffer_to_qpixmap: Fehler | Dateigröße: {len(buffer) if isinstance(buffer, (bytes, bytearray)) else 'N/A'} bytes",
            exc_info=True
        )
        return QPixmap()