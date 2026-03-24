import threading
import subprocess
import sys
import time
from pathlib import Path

from typing import * 

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

from application.settings import settings

from instances.project_scheduler import ProjectScheduler
from ui.aspect_ratio_label import AspectRatioLabel
from ui.ui_mainwindow import Ui_MainWindow
from ui.ui_destinationalreadyexists import Ui_Dialog as Ui_D_Dialog
from ui.ui_rotatepart import Ui_Dialog as Ui_R_Dialog

from instances.serial_device import SerialDevice
from instances.camera_crane import CameraCrane
from instances.turn_table import TurnTable

from instances.camera import Camera

from application.datastructures import Image
import application.file_processing as fp 

class RotatePartDialog(QDialog):
    def __init__(self):
        super().__init__()

        self.ui = Ui_R_Dialog()
        self.ui.setupUi(self)

        self.movie = QMovie("assets/rotate_part.gif")

        if self.movie.isValid():
            self.ui.label_movie.setMovie(self.movie)
            self.movie.start()


class DestinationAlreadyExistsDialog(QDialog):
    def __init__(self, article_number: str = None):
        super().__init__()

        self.ui = Ui_D_Dialog()
        self.ui.setupUi(self)

        self.ui.label_article_number.setText(article_number or "00000")

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self.serial_device = SerialDevice()
        self.turn_table = TurnTable(self.serial_device)
        self.camera_crane = CameraCrane(self.serial_device)
        self.camera = Camera()

        self.project_scheduler = ProjectScheduler(
            camera=self.camera,
            serial_device=self.serial_device,
            camera_crane=self.camera_crane,
            turn_table=self.turn_table,
        )

        self.serial_device.start()
        self.turn_table.start()
        self.camera_crane.start()
        self.camera.start()

        self.project_scheduler.start()

        self.project_started_at: Optional[float] = None

        self._replace_image_label()
        self._init_ui_from_settings()
        self._connect_ui()

        self.ui_timer = QTimer(interval=int(1000 / settings.ui.refreshrate))
        self.ui_timer.timeout.connect(self._update_ui)
        self.ui_timer.start()

        self.preview_timer = QTimer(interval=int(1000 / settings.ui.preview_refreshrate))
        self.preview_timer.timeout.connect(self._update_preview)
        self.preview_timer.start()

        self.preview: Optional[Image] = None
        self.preview_bytes = bytes()

        self.preview_bytes = Path("pic.jpg").read_bytes() # TODO: entfernen

    def _replace_image_label(self):
        old_label = self.ui.image_label
        parent_layout = self.ui.horizontalLayout

        new_label = AspectRatioLabel(self.centralWidget(), aspect_ratio = 16 / 9)
        new_label.setObjectName("image_label")

        index = parent_layout.indexOf(old_label)
        parent_layout.removeWidget(old_label)
        old_label.deleteLater()

        parent_layout.insertWidget(index, new_label)
        self.ui.image_label = new_label

    def _init_ui_from_settings(self):
        self.ui.base_tv_input.setText(str(settings.camera.base_tv))
        self.ui.hdr_ev_input.setValue(settings.camera.hdr_ev)
        self.ui.hdr_count_input.setValue(settings.camera.hdr_shot_count)

        self.ui.crop_slider.setValue(int(round(settings.app.image_crop * 100)))

        self.ui.contrast_slider.setValue(int(round(settings.camera.contrast_weight * 100)))
        self.ui.exposure_slider.setValue(int(round(settings.camera.exposure_weight * 100)))
        self.ui.saturation_slider.setValue(int(round(settings.camera.saturation_weight * 100)))

        self.ui.liveview_checkbox.setChecked(False)

        self.ui.single_picture_button.setChecked((not settings.camera.use_mertens and not settings.camera.use_robertson))
        self.ui.hdr_mertens_button.setChecked(settings.camera.use_mertens)
        self.ui.hdr_robertson_button.setChecked(settings.camera.use_robertson)

        self.reset_progress_ui()

    def _connect_ui(self):
        self.ui.base_tv_input.textChanged.connect(self._on_base_tv_changed)
        self.ui.hdr_ev_input.valueChanged.connect(self._on_hdr_ev_changed)
        self.ui.hdr_count_input.valueChanged.connect(self._on_hdr_count_changed)

        self.ui.crop_slider.sliderMoved.connect(self._on_crop_change)
        self.ui.crop_slider.sliderReleased.connect(self._on_crop_changed)

        self.ui.contrast_slider.sliderReleased.connect(self._on_contrast_changed)
        self.ui.exposure_slider.sliderReleased.connect(self._on_exposure_changed)
        self.ui.saturation_slider.sliderReleased.connect(self._on_saturation_changed)

        self.ui.single_picture_button.clicked.connect(self._on_radio_button_changed)
        self.ui.hdr_mertens_button.clicked.connect(self._on_radio_button_changed)
        self.ui.hdr_robertson_button.clicked.connect(self._on_radio_button_changed)

        self.ui.start_button.clicked.connect(self._on_start_clicked)
        self.ui.pause_button.clicked.connect(self._on_pause_clicked)
        self.ui.stop_button.clicked.connect(self._on_stop_clicked)

        self.ui.hdr_preview_button.clicked.connect(self._on_hdr_preview_clicked)

        self.ui.settings_button.clicked.connect(self._open_settings_folder)

    ###
    def set_preview_pixmap(self, pixmap: QPixmap):
        if pixmap and not pixmap.isNull():
            self.ui.image_label.setPixmap(pixmap)

    def reset_progress_ui(self):
        self.ui.progress_bar.setRange(0, 100)
        self.ui.progress_bar.setValue(0)
        self.ui.progress_bar.setFormat("0/0")
        self.ui.time_label.setText("0:00 min")
        self.ui.pause_button.setText("Pause")

    ## Update
    def _update_hardware_visuals(self):
        ready = self.camera.is_connected() and self.serial_device.is_connected()

        self.ui.start_button.setEnabled(ready)
        self.ui.pause_button.setEnabled(ready)
        self.ui.stop_button.setEnabled(ready)

        if not self.camera.is_connected():
            self.ui.hdr_preview_button.setEnabled(False)
            self.ui.liveview_checkbox.setEnabled(False)
        else:
            self.ui.hdr_preview_button.setEnabled(not self.ui.single_picture_button)
            self.ui.liveview_checkbox.setEnabled(True)

        self.ui.lcd_crane_pos.display(round(getattr(self.camera_crane, "position", 0.0), 2) * 100)
        self.ui.lcd_table_pos.display(round(getattr(self.turn_table, "rotation", 0.0), 1) % 360)
    
    def _update_status_bar(self):
        if self.camera.is_connected() and self.serial_device.is_connected():
            self.statusBar().showMessage("[2/2] | Hardware bereit")
        elif not self.camera.is_connected() and not self.serial_device.is_connected():
            self.statusBar().showMessage("[0/2] | Hardware nicht bereit")
        elif not self.camera.is_connected():
            self.statusBar().showMessage("[1/2] | Serial Getrennt | Kamera verbunden")
        elif not self.serial_device.is_connected():
            self.statusBar().showMessage("[1/2] | Serial Verbunden | Kamera Getrennt")

    def _block_settings_while_running(self):
        elements: list[QLabel] = [self.ui.name_input, self.ui.base_tv_input, self.ui.crop_slider, self.ui.contrast_slider, self.ui.exposure_slider, self.ui.saturation_slider, self.ui.hdr_count_input, self.ui.hdr_ev_input, self.ui.hdr_mertens_button, self.ui.hdr_robertson_button, self.ui.single_picture_button, self.ui.start_button, self.ui.hdr_preview_button]
        
        def set_state(state: bool):
            for e in elements:
                if not state and e.isEnabled():
                    e.setEnabled(state)
                elif state and not e.isEnabled():
                    if e in [self.ui.contrast_slider, self.ui.exposure_slider, self.ui.saturation_slider]:
                        e.setEnabled(self.ui.hdr_mertens_button.isChecked())
                    elif e in [self.ui.hdr_count_input, self.ui.hdr_ev_input]:
                        e.setEnabled(not self.ui.single_picture_button.isChecked())
                    elif e == self.ui.hdr_preview_button:
                        e.setEnabled(not self.ui.liveview_checkbox.isChecked())
                    else:
                        e.setEnabled(state)
        
        if self.project_scheduler.current_project and self.project_scheduler.is_project_running():
            set_state(False)
        else:
            set_state(True)

    def _handle_rotate_dialog(self):
        project = self.project_scheduler.current_project
        if project is None:
            return

        needs_turn = (
            self.project_scheduler.is_project_running()
            and project.current_index == project.turn_index
            and not project.turn_confirmed
        )

        if needs_turn:
            result = self.show_rotate_dialog()

            if result:
                self.project_scheduler.confirm_turn()

    def _update_project_progress(self):
        project = self.project_scheduler.current_project
        if project is None:
            return

        total = max(1, project.n_total_shots)
        finished = min(project.n_finished_shots, total)

        percent = int((finished / total) * 100)

        self.ui.progress_bar.setValue(percent)
        self.ui.progress_bar.setFormat(f"{finished}/{project.n_total_shots}")

        if self.project_started_at is not None:
            elapsed = int(time.time() - self.project_started_at)
            minutes = elapsed // 60
            seconds = elapsed % 60
            self.ui.time_label.setText(f"{minutes}:{seconds:02d} min")

    def _update_ui(self):
        self._block_settings_while_running()
        self._update_status_bar()
        self._update_hardware_visuals()
        self._handle_rotate_dialog()
        self._update_project_progress()

    def _update_preview(self):        
        if self.camera.is_connected() and self.ui.liveview_checkbox.isChecked():
            self.preview = Image(data=self.camera.liveview_data)
            self.preview.crop(settings.app.image_crop)
        elif self.preview_bytes:
            self.preview = Image(self.preview_bytes)
            self.preview.crop(settings.app.image_crop)
        else:
            return
        
        pixmap = self.preview.get_pixmap()

        self.set_preview_pixmap(pixmap)

    # ---------------------------------------------------------
    # Action Knöpfe
    # ---------------------------------------------------------

    def _on_hdr_preview_clicked(self):
        if not self.camera.is_connected():
            return
        
        self.ui.hdr_preview_button.setEnabled(False)

        def worker():
            try:
                payloads = self.project_scheduler._create_image_payloads()
                images: list[Image] = []

                for payload in payloads:
                    result = self.camera.queue_shot(payload).result(settings.camera.timeout)

                    if not result or result.image is None:
                        raise RuntimeError("Bildaufnahme fehlgeschlagen")

                    images.append(result.image)

                cv_images = []
                for image in images:
                    cv_img = image.get_cv2_image()
                    if cv_img is None:
                        raise RuntimeError("Bild konnte nicht dekodiert werden")
                    cv_images.append(cv_img)

                if len(cv_images) == 0:
                    raise RuntimeError("Keine Bilder für Preview vorhanden")

                if len(cv_images) == 1:
                    result_img = cv_images[0].copy()

                elif settings.camera.use_mertens:
                    result_img = fp.hdr_merge_mertens_buffer(
                        images=cv_images,
                        contrast=settings.camera.contrast_weight,
                        exposure=settings.camera.exposure_weight,
                        saturation=settings.camera.saturation_weight,
                    )

                elif settings.camera.use_robertson:
                    exposure_times = [payload.tv for payload in payloads]

                    result_img = fp.hdr_merge_robertson_buffer(
                        images=cv_images,
                        exposure_times=exposure_times,
                        gamma=settings.camera.tonemap_gamma,
                    )

                else:
                    result_img = cv_images[0].copy()

                if result_img is None:
                    raise RuntimeError("HDR-Verarbeitung fehlgeschlagen")

                if settings.app.image_crop > 0:
                    cropped = fp.crop_image_buffer(result_img, settings.app.image_crop)
                    if cropped is None:
                        raise RuntimeError("Crop fehlgeschlagen")
                    result_img = cropped

                preview_image = Image()
                preview_image.cv2_to_data(result_img)

                if not preview_image.data:
                    raise RuntimeError("Preview konnte nicht encodiert werden")

                self.preview_bytes = preview_image.data

            except Exception as e:
                self.statusBar().showMessage(f"HDR-Preview fehlgeschlagen: {e}")

            finally:
                self.ui.hdr_preview_button.setEnabled(True)

        threading.Thread(target=worker, daemon=True).start()

    def _on_start_clicked(self):
        if not self.camera.is_connected() or not self.serial_device.is_connected():
            return

        name = self.ui.name_input.text().strip()

        if not name:
            self.statusBar().showMessage("Bitte einen Namen eingeben")
            return

        dst = Path(settings.process.destination_dir)

        project_dst = dst / name
        if project_dst.exists():
            result = self.show_destination_already_exists_dialog()
            if not result:
                return

        project = self.project_scheduler.create_project(name, dst)
        if project is None:
            self.statusBar().showMessage("Projekt konnte nicht erstellt werden")
            return

        self.project_scheduler.current_project = project
        self.project_started_at = time.time()

        self.reset_progress_ui()
        self.project_scheduler.start_project()

    def _on_pause_clicked(self):
        if not self.project_scheduler.is_project_running():
            return

        if self.project_scheduler.is_project_paused():
            self.project_scheduler.resume_project()
            self.ui.pause_button.setText("Pause")
        else:
            self.project_scheduler.pause_project()
            self.ui.pause_button.setText("Fortsetzen")

    def _on_stop_clicked(self):
        self.project_scheduler.stop_project()
        self.project_scheduler.current_project = None
        self.project_started_at = None
        self.reset_progress_ui()

    # ---------------------------------------------------------
    # Dialoge
    # ---------------------------------------------------------

    def show_rotate_dialog(self) -> bool:
        dlg = RotatePartDialog()
        dlg.show()

        return dlg.exec()

    def show_destination_already_exists_dialog(self) -> bool:
        dlg = DestinationAlreadyExistsDialog(self.ui.name_input.text())
        dlg.show()

        return dlg.exec()

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
        settings.save()

        self.camera.set_camera_properties(settings.camera.iso, settings.camera.av, settings.camera.base_tv)

    def _on_hdr_ev_changed(self, value):
        settings.camera.hdr_ev = float(value)
        settings.save()

    def _on_hdr_count_changed(self, value):
        if value % 2 == 0:
            return

        settings.camera.hdr_shot_count = int(value)
        settings.save()

    def _on_crop_change(self):
        settings.app.image_crop = min(max(self.ui.crop_slider.value() / 100, 0), 1)

    def _on_crop_changed(self):
        settings.app.image_crop = min(max(self.ui.crop_slider.value() / 100, 0), 1)
        settings.save()

    def _on_contrast_changed(self):
        settings.camera.contrast_weight = min(max(self.ui.contrast_slider.value() / 100, 0), 1)
        settings.save()

    def _on_exposure_changed(self):
        settings.camera.exposure_weight = min(max(self.ui.exposure_slider.value() / 100, 0), 1)
        settings.save()

    def _on_saturation_changed(self):
        settings.camera.saturation_weight = min(max(self.ui.saturation_slider.value() / 100, 0), 1)
        settings.save()

    def _on_radio_button_changed(self):
        settings.camera.use_mertens   = self.ui.hdr_mertens_button.isChecked() and not self.ui.single_picture_button.isChecked()
        settings.camera.use_robertson = self.ui.hdr_robertson_button.isChecked() and not self.ui.single_picture_button.isChecked()
        settings.save()

    def _open_settings_folder(self):
        settings_path = Path(__file__).resolve().parent / "application" / "settings.json"

        settings_path = settings_path.resolve()

        if settings_path.exists():
            if sys.platform == "win32":
                subprocess.Popen(["explorer", "/select,", str(settings_path)])
            else:
                QDesktopServices.openUrl(QUrl.fromLocalFile(str(settings_path.parent)))
        else:
            self.statusBar().showMessage(f"Settings-Datei nicht gefunden: {settings_path}")

    def closeEvent(self, event):
        for instance in (
            self.project_scheduler,
            self.camera,
            self.camera_crane,
            self.turn_table,
            self.serial_device,
        ):
            try:
                instance.stop()
            except Exception:
                pass

        super().closeEvent(event)
        

if __name__ == "__main__":
    app = QApplication(sys.argv)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())