import sys
import time
from pathlib import Path

from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QDialog,
    QVBoxLayout,
    QLabel,
    QPushButton,
)
from PySide6.QtCore import QTimer, QUrl, Qt
from PySide6.QtGui import QDesktopServices, QMovie, QPixmap

from ui.aspect_ratio_label import AspectRatioLabel
from ui.ui_mainwindow import Ui_MainWindow

from serial_device import SerialDevice
from turn_table import TurnTable
from camera_crane import CameraCrane
from camera import Camera
from ai_project_scheduler import ProjectScheduler, SchedulerPhase

from application.settings import settings, file as settings_file
import framework.file_processing as fp


class TurnPartDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Teil drehen")
        self.setModal(True)
        self.setMinimumWidth(360)

        layout = QVBoxLayout(self)

        self.gif_label = QLabel(self)
        self.gif_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.movie = QMovie("assets/turn_part.gif")
        if self.movie.isValid():
            self.gif_label.setMovie(self.movie)
            self.movie.start()

        text = QLabel(
            "Bitte das Teil jetzt drehen.\n\n"
            "Wenn das Teil richtig gedreht ist, mit OK fortfahren.",
            self,
        )
        text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        text.setWordWrap(True)

        ok_button = QPushButton("OK", self)
        ok_button.clicked.connect(self.accept)

        layout.addWidget(self.gif_label)
        layout.addWidget(text)
        layout.addWidget(ok_button)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self.setWindowTitle("DFGM - PIZZA")

        self.serial_device = SerialDevice()
        self.turn_table = TurnTable(self.serial_device)
        self.camera_crane = CameraCrane(self.serial_device)
        self.camera = Camera()
        self.project_scheduler = ProjectScheduler(
            camera=self.camera,
            serial_device=self.serial_device,
            turn_table=self.turn_table,
            camera_crane=self.camera_crane,
        )

        self.serial_device.start()
        self.turn_table.start()
        self.camera_crane.start()
        self.camera.start()
        self.project_scheduler.start()

        self.current_project = None
        self.project_started_at: float | None = None
        self._turn_dialog_open = False

        self._replace_image_label()

        self._init_ui_from_settings()
        self._prepare_mode_buttons()
        self._connect_ui()
        self._update_hdr_preview_enabled()
        self._reset_progress_ui()

        self.update_timer = QTimer(self)

        interval_ms = int(1000 / settings.ui.refreshrate)
        self.update_timer.setInterval(interval_ms)

        self.update_timer.timeout.connect(self._update_ui)
        self.update_timer.start()

    def _replace_image_label(self):
        old_label = self.ui.image_label
        parent_layout = self.ui.horizontalLayout

        new_label = AspectRatioLabel(self.centralWidget(), aspect_ratio=16 / 9)
        new_label.setObjectName("image_label")

        index = parent_layout.indexOf(old_label)
        parent_layout.removeWidget(old_label)
        old_label.deleteLater()

        parent_layout.insertWidget(index, new_label)
        self.ui.image_label = new_label

    def set_preview_pixmap(self, pixmap: QPixmap):
        if pixmap and not pixmap.isNull():
            self.ui.image_label.setPixmap(pixmap)

    def _init_ui_from_settings(self):
        self.ui.base_tv_input.setText(str(settings.camera.base_tv))
        self.ui.hdr_ev_input.setValue(settings.camera.hdr_ev)
        self.ui.hdr_count_input.setValue(settings.camera.hdr_shot_count)

        self.ui.contrast_slider.setValue(int(round(settings.camera.contrast_weight * 100)))
        self.ui.exposure_slider.setValue(int(round(settings.camera.exposure_weight * 100)))
        self.ui.saturation_slider.setValue(int(round(settings.camera.saturation_weight * 100)))

        self.ui.liveview_checkbox.setChecked(True)

    def _prepare_mode_buttons(self):
        for button in (
            self.ui.single_picture_button,
            self.ui.hdr_mertens_button,
            self.ui.hdr_robertson_button,
        ):
            try:
                button.setCheckable(True)
            except Exception:
                pass

        if settings.camera.use_robertson:
            self.ui.hdr_robertson_button.setChecked(True)
            self.ui.hdr_mertens_button.setChecked(False)
            self.ui.single_picture_button.setChecked(False)
        elif settings.camera.use_mertens:
            self.ui.hdr_mertens_button.setChecked(True)
            self.ui.hdr_robertson_button.setChecked(False)
            self.ui.single_picture_button.setChecked(False)
        else:
            self.ui.single_picture_button.setChecked(True)
            self.ui.hdr_mertens_button.setChecked(False)
            self.ui.hdr_robertson_button.setChecked(False)

    def _connect_ui(self):
        self.ui.base_tv_input.textChanged.connect(self._on_base_tv_changed)
        self.ui.hdr_ev_input.valueChanged.connect(self._on_hdr_ev_changed)
        self.ui.hdr_count_input.valueChanged.connect(self._on_hdr_count_changed)

        self.ui.start_button.clicked.connect(self._on_start_clicked)
        self.ui.pause_button.clicked.connect(self._on_pause_clicked)
        self.ui.stop_button.clicked.connect(self._on_stop_clicked)

        self.ui.contrast_slider.sliderReleased.connect(self._on_contrast_changed)
        self.ui.exposure_slider.sliderReleased.connect(self._on_exposure_changed)
        self.ui.saturation_slider.sliderReleased.connect(self._on_saturation_changed)

        self.ui.single_picture_button.clicked.connect(self._set_single_picture_mode)
        self.ui.hdr_mertens_button.clicked.connect(self._set_hdr_mertens_mode)
        self.ui.hdr_robertson_button.clicked.connect(self._set_hdr_robertson_mode)

        self.ui.liveview_checkbox.toggled.connect(self._on_liveview_toggled)
        self.ui.hdr_preview_button.clicked.connect(self._on_hdr_preview_clicked)

        self.ui.settings_button.clicked.connect(self._open_settings_folder)

    # ---------------------------------------------------------
    # Helpers
    # ---------------------------------------------------------

    def _open_settings_folder(self):
        try:
            settings_path = settings_file
            folder = settings_path.parent

            QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))

        except Exception as e:
            print("Failed to open settings folder:", e)

    def _save_settings(self):
        settings.save()

    def _set_mode_buttons(self, single: bool, mertens: bool, robertson: bool):
        self.ui.single_picture_button.setChecked(single)
        self.ui.hdr_mertens_button.setChecked(mertens)
        self.ui.hdr_robertson_button.setChecked(robertson)

    def _update_hdr_preview_enabled(self):
        liveview_enabled = self.ui.liveview_checkbox.isChecked()
        single_mode = self.ui.single_picture_button.isChecked()
        self.ui.hdr_preview_button.setEnabled(not liveview_enabled and not single_mode)

    def _reset_progress_ui(self):
        self.ui.progress_bar.setRange(0, 100)
        self.ui.progress_bar.setValue(0)
        self.ui.progress_bar.setFormat("0/0")
        self.ui.time_label.setText("0:00 min")
        self.ui.pause_button.setText("Pause")

    def _format_elapsed(self) -> str:
        if not self.project_started_at:
            return "0:00 min"

        elapsed = max(0, int(time.time() - self.project_started_at))
        minutes = elapsed // 60
        seconds = elapsed % 60
        return f"{minutes}:{seconds:02d} min"

    def _show_turn_dialog(self):
        if self._turn_dialog_open:
            return

        self._turn_dialog_open = True
        try:
            dialog = TurnPartDialog(self)
            result = dialog.exec()

            if result == QDialog.DialogCode.Accepted:
                self.project_scheduler.confirm_turn_done()
        finally:
            self._turn_dialog_open = False

    def _try_load_latest_preview(self):
        project = self.current_project
        if not project:
            return

        preview_dir = Path(project.dir_destination) / "preview"
        if preview_dir.exists():
            previews = sorted(
                preview_dir.glob("*.jpg"),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
            if previews:
                self.set_preview_pixmap(QPixmap(str(previews[0])))
                return

        images = sorted(
            Path(project.dir_destination).glob("*.jpg"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if images:
            self.set_preview_pixmap(QPixmap(str(images[0])))

    # ---------------------------------------------------------
    # Input handlers
    # ---------------------------------------------------------

    def _on_base_tv_changed(self, text: str):
        text = text.strip().replace(",", ".")

        if not text:
            return

        try:
            value = float(text)
        except ValueError:
            return

        if value <= 0:
            return

        settings.camera.base_tv = value
        self._save_settings()

    def _on_hdr_ev_changed(self, value):
        settings.camera.hdr_ev = float(value)
        self._save_settings()

    def _on_hdr_count_changed(self, value):
        settings.camera.hdr_shot_count = int(value)
        self._save_settings()

    def _on_contrast_changed(self):
        settings.camera.contrast_weight = self.ui.contrast_slider.value() / 100
        self._save_settings()

    def _on_exposure_changed(self):
        settings.camera.exposure_weight = self.ui.exposure_slider.value() / 100
        self._save_settings()

    def _on_saturation_changed(self):
        settings.camera.saturation_weight = self.ui.saturation_slider.value() / 100
        self._save_settings()

    # ---------------------------------------------------------
    # Mode handlers
    # ---------------------------------------------------------

    def _set_single_picture_mode(self):
        settings.camera.use_mertens = False
        settings.camera.use_robertson = False
        self._set_mode_buttons(True, False, False)
        self._save_settings()
        self._update_hdr_preview_enabled()

    def _set_hdr_mertens_mode(self):
        settings.camera.use_mertens = True
        settings.camera.use_robertson = False
        self._set_mode_buttons(False, True, False)
        self._save_settings()
        self._update_hdr_preview_enabled()

    def _set_hdr_robertson_mode(self):
        settings.camera.use_mertens = False
        settings.camera.use_robertson = True
        self._set_mode_buttons(False, False, True)
        self._save_settings()
        self._update_hdr_preview_enabled()

    # ---------------------------------------------------------
    # Control buttons
    # ---------------------------------------------------------

    def _devices_ready(self) -> bool:
        try:
            camera_connected = self.camera.is_connected()
        except Exception:
            camera_connected = False

        try:
            serial_connected = self.serial_device.is_connected()
        except Exception:
            serial_connected = False

        return camera_connected and serial_connected

    def _on_start_clicked(self):
        if not self._devices_ready():
            self.ui.status_label.setText("Start nicht möglich: Kamera oder Serial Device nicht verbunden")
            return

        if self.project_scheduler.project_running.is_set():
            return

        if self.current_project is None:
            name = self.ui.name_input.text().strip()

            if not name:
                name = None

            if not len(name) == 5:
                self.ui.status_label.setText("Artikelnummer ungültig - muss 5 stellig sein")
                return
            
            if (Path(settings.process.destination_dir) / name).exists():
                self.ui.status_label.setText("DFGM für Artikelnummer existiert bereits - erneut starten um zu überschreiben")
                return

            self.current_project = self.project_scheduler.generate_project(name=name)

        self.project_started_at = time.time()
        self.ui.progress_bar.setRange(0, 100)
        self.ui.progress_bar.setValue(0)
        self.ui.pause_button.setText("Pause")

        self.project_scheduler.start_project(self.current_project)

    def _on_pause_clicked(self):
        if not self._devices_ready():
            self.ui.status_label.setText("Stop nicht möglich: Kamera oder Serial Device nicht verbunden")
            return
        
        if not self._devices_ready():
            self.ui.status_label.setText("Pause/Weiter nicht möglich: Kamera oder Serial Device nicht verbunden")
            return
        
        if not self.current_project or not self.project_scheduler.project_running.is_set():
            return

        if self.project_scheduler.project_paused.is_set():
            self.project_scheduler.resume_project()
            self.ui.pause_button.setText("Pause")
        else:
            self.project_scheduler.pause_project()
            self.ui.pause_button.setText("Weiter")

    def _on_stop_clicked(self):
        self.project_scheduler.stop_project()
        self.current_project = None
        self.project_started_at = None
        self._turn_dialog_open = False
        self._reset_progress_ui()
        self.ui.status_label.setText("Gestoppt")

    # ---------------------------------------------------------
    # Liveview / preview
    # ---------------------------------------------------------

    def _on_liveview_toggled(self, checked: bool):
        self._update_hdr_preview_enabled()

    def _on_hdr_preview_clicked(self):
        if not self.ui.hdr_preview_button.isEnabled():
            return

    def _update_ui(self):
        try:
            camera_connected = self.camera.is_connected()
        except Exception:
            camera_connected = False

        try:
            serial_connected = self.serial_device.is_connected()
        except Exception:
            serial_connected = False

        devices_ready = camera_connected and serial_connected

        self.ui.start_button.setEnabled(devices_ready)
        self.ui.pause_button.setEnabled(devices_ready)
        self.ui.stop_button.setEnabled(devices_ready)

        self.ui.lcd_crane_pos.display(round(getattr(self.camera_crane, "position", 0.0), 2)*100)
        self.ui.lcd_table_pos.display(round(getattr(self.turn_table, "rotation", 0.0), 1) % 360)

        project = self.current_project

        if project is not None:
            total_jobs = max(0, int(project.state.total_jobs))
            finished_jobs = max(0, int(project.state.finished_jobs))

            if total_jobs > 0:
                self.ui.progress_bar.setRange(0, total_jobs)
                self.ui.progress_bar.setValue(min(finished_jobs, total_jobs))
                self.ui.progress_bar.setFormat(f"{finished_jobs}/{total_jobs}")
            else:
                self.ui.progress_bar.setRange(0, 100)
                self.ui.progress_bar.setValue(0)
                self.ui.progress_bar.setFormat("0/0")

            self.ui.time_label.setText(self._format_elapsed())
            self._try_load_latest_preview()

            if project.state.error:
                self.ui.status_label.setText(f"Fehler: {project.state.error}")
            elif self.project_scheduler.phase == SchedulerPhase.WAIT_USER_TURN:
                self.ui.status_label.setText("Bitte Teil drehen")
                self._show_turn_dialog()
            elif self.project_scheduler.project_paused.is_set():
                self.ui.status_label.setText("Pausiert")
            elif self.project_scheduler.phase == SchedulerPhase.FINISHED:
                self.ui.status_label.setText("Fertig")
                self.ui.pause_button.setText("Pause")
            elif self.project_scheduler.project_running.is_set():
                self.ui.status_label.setText("Läuft")
        else:
            self.ui.progress_bar.setRange(0, 100)
            self.ui.progress_bar.setValue(0)
            self.ui.progress_bar.setFormat("0/0")
            self.ui.time_label.setText("0:00 min")
        if camera_connected and serial_connected:
            self.statusBar().showMessage("System ready")
        elif not serial_connected and not camera_connected:
            self.statusBar().showMessage("Serial device and Camera disconnected")
        elif not serial_connected:
            self.statusBar().showMessage("Serial device disconnected")
        elif not camera_connected:
            self.statusBar().showMessage("Camera disconnected")

        if (
            self.current_project is not None
            and self.project_scheduler.phase == SchedulerPhase.FINISHED
            and not self.project_scheduler.project_running.is_set()
        ):
            # Projekt fürs UI behalten, aber als abgeschlossen behandeln
            self.ui.pause_button.setText("Pause")

    def closeEvent(self, event):
        for instance in (
            self.project_scheduler,
            self.camera,
            self.camera_crane,
            self.turn_table,
            self.serial_device,
        ):
            try:
                instance.shutdown()
            except Exception:
                pass

        super().closeEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())