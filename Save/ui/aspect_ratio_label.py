from __future__ import annotations

from PySide6.QtCore import Qt, QSize, QRect
from PySide6.QtGui import QPainter, QPixmap, QColor
from PySide6.QtWidgets import QLabel, QSizePolicy


class AspectRatioLabel(QLabel):
    def __init__(self, parent=None, aspect_ratio: float = 16 / 9):
        super().__init__(parent)

        self._aspect_ratio = aspect_ratio
        self._pixmap: QPixmap | None = None
        self._background_color = QColor(15, 15, 15)

        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(160, 90)

    def setAspectRatio(self, aspect_ratio: float) -> None:
        if aspect_ratio <= 0:
            return
        self._aspect_ratio = aspect_ratio
        self.updateGeometry()
        self.update()

    def aspectRatio(self) -> float:
        return self._aspect_ratio

    def setPixmap(self, pixmap: QPixmap) -> None:
        self._pixmap = pixmap
        self.update()

    def clear(self) -> None:
        self._pixmap = None
        super().clear()
        self.update()

    def hasHeightForWidth(self) -> bool:
        return True

    def heightForWidth(self, width: int) -> int:
        return int(width / self._aspect_ratio)

    def sizeHint(self) -> QSize:
        width = max(self.width(), 320)
        return QSize(width, self.heightForWidth(width))

    def minimumSizeHint(self) -> QSize:
        return QSize(160, 90)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        # Hintergrund
        painter.fillRect(self.rect(), self._background_color)

        if not self._pixmap or self._pixmap.isNull():
            return

        target = self._get_target_rect()
        scaled = self._pixmap.scaled(
            target.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

        x = target.x() + (target.width() - scaled.width()) // 2
        y = target.y() + (target.height() - scaled.height()) // 2

        painter.drawPixmap(x, y, scaled)

    def _get_target_rect(self) -> QRect:
        available_w = self.width()
        available_h = self.height()

        if available_w <= 0 or available_h <= 0:
            return QRect()

        target_w = available_w
        target_h = int(target_w / self._aspect_ratio)

        if target_h > available_h:
            target_h = available_h
            target_w = int(target_h * self._aspect_ratio)

        x = (available_w - target_w) // 2
        y = (available_h - target_h) // 2

        return QRect(x, y, target_w, target_h)