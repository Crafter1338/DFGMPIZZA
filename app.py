from typing import * 
###############################
import threading
from pathlib import Path
import subprocess
import sys
import time
###############################
import logging
from logging.handlers import RotatingFileHandler

app_dir = Path(__file__).resolve().parent
log_dir = app_dir / "application"
log_dir.mkdir(parents=True, exist_ok=True)
log_file = log_dir / "app.log"

file_handler = RotatingFileHandler(
    log_file,
    maxBytes=5 * 1024 * 1024,
    backupCount=2,
    encoding="utf-8",
)
file_handler.setFormatter(
    logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
)

logging.basicConfig(
    level=logging.DEBUG,
    handlers=[
        logging.StreamHandler(),
        file_handler,
    ],
)
logger = logging.getLogger(__name__)
###############################
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

from ui.ui_destinationalreadyexists import Ui_Dialog as Ui_D_Dialog
from ui.ui_rotatepart import Ui_Dialog as Ui_R_Dialog
from ui.ui_invalidarticle import Ui_Dialog as Ui_I_Dialog
from ui.ui_projectfinished import Ui_Dialog as Ui_P_Dialog
###############################
from application.settings import settings

from instances.serial_device import SerialDevice
from instances.camera_crane import CameraCrane
from instances.turn_table import TurnTable

from instances.camera import Camera
import application.file_processing as fp

from instances.project_scheduler import Project, ProjectScheduler
###############################
from application.datastructures import Image

## Helpers ####################
def _parse_float(self, text: str):
    try:
        return float(text.strip().replace(",", "."))
    except ValueError:
        return None

def _clamp01(self, value: float):
    return min(max(value, 0), 1)

def _set_and_save(self, obj, attr: str, value):
    setattr(obj, attr, value)
    settings.save()

## Dialoge / Pop-Ups ##########
class RotatePartDialog(QDialog):
    def __init__(self):
        super().__init__()

        self.ui = Ui_R_Dialog()
        self.ui.setupUi(self)

        self.movie = QMovie("assets/rotate_part.gif") # TODO: Rotate Part GIF

        if self.movie.isValid():
            self.ui.label_movie.setMovie(self.movie)
            self.movie.start()
            
class InvalidArticleNumberDialog(QDialog):
    def __init__(self):
        super().__init__()

        self.ui = Ui_I_Dialog()
        self.ui.setupUi(self)
        
class DestinationAlreadyExistsDialog(QDialog):
    def __init__(self, article_number: str = None):
        super().__init__()

        self.ui = Ui_D_Dialog()
        self.ui.setupUi(self)

        self.ui.label_article_number.setText(article_number or "")

class ProjectFinishedDialog(QDialog):
    def __init__(self, path: Path):
        super().__init__()

        self.ui = Ui_P_Dialog()
        self.ui.setupUi(self)
        
        self.ui.path_label.setText(str(Path(path.absolute())))
      
## Main Window ################
class MainWindow(QMainWindow):
    ## Init #######################
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
        
        self.project: Optional[Project] = None
        
        self._replace_image_label()
        self._init_ui_from_settings()
        self._connect_ui()

        self.ui_timer = QTimer(interval=int(1000 / settings.ui.refreshrate))
        self.ui_timer.timeout.connect(self.update_ui)
        self.ui_timer.start()

        self.preview_timer = QTimer(interval=int(1000 / settings.ui.preview_refreshrate))
        self.preview_timer.timeout.connect(self.update_preview)
        self.preview_timer.start()

        self.preview: Optional[Image] = None
        self.preview_bytes = bytes()
        
    ## UI Helpers #################
    def _replace_image_label(self): # Sorgt dafür, dass jedes Image im Preview auch wirklich 16:9 ist
        old_label = self.ui.image_label
        parent_layout = self.ui.horizontalLayout

        new_label = AspectRatioLabel(self.centralWidget(), aspect_ratio = 16 / 9)
        new_label.setObjectName("image_label")

        index = parent_layout.indexOf(old_label)
        parent_layout.removeWidget(old_label)
        old_label.deleteLater()

        parent_layout.insertWidget(index, new_label)
        self.ui.image_label = new_label

    def _init_ui_from_settings(self): # Stellt das UI von den Settings ein
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

        self._reset_progress_ui()

    def _connect_ui(self): # Verbindet das UI mit den Settings
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

        self.ui.settings_button.clicked.connect(self.open_settings_folder)
        
    def _set_preview_pixmap(self, pixmap: QPixmap):
        if pixmap and not pixmap.isNull():
            self.ui.image_label.setPixmap(pixmap)

    def _reset_progress_ui(self):
        self.ui.progress_bar.setRange(0, 100)
        self.ui.progress_bar.setValue(0)
        self.ui.progress_bar.setFormat("0/0")
        self.ui.time_label.setText("0:00 min")
        self.ui.pause_button.setText("Pause")
        
    ## Update UI ##################
    def _update_hardware_visuals(self):
        self.ui.lcd_crane_pos.display(round(getattr(self.camera_crane, "position", 0.0), 2) * 100)
        self.ui.lcd_table_pos.display(round(getattr(self.turn_table, "rotation", 0.0), 1) % 360)
    
    def _update_status_bar(self):
        if self.camera.is_connected() and self.serial_device.is_connected() and self.camera_crane.is_nulling:
            self.statusBar().showMessage("[2/3] | Hardware wird vorbereitet...")
        elif not self.camera.is_connected() and not self.serial_device.is_connected():
            self.statusBar().showMessage("[0/3] | Hardware nicht bereit")
        elif not self.camera.is_connected():
            self.statusBar().showMessage("[1/3] | Serial Verbunden | Kamera Getrennt")
        elif not self.serial_device.is_connected():
            self.statusBar().showMessage("[1/3] | Serial Getrennt | Kamera Verbunden")

    def _block_settings_while_running(self):
        is_project_running = self.project_scheduler.is_project_running()
        is_cam_connected = self.camera.is_connected()
        is_serial_connected = self.serial_device.is_connected()

        is_system_ready = is_cam_connected and is_serial_connected and self.camera_crane.nulled.is_set() and self.turn_table.nulled.is_set()

        self.ui.name_input.setEnabled(is_system_ready and not is_project_running)

        self.ui.single_picture_button.setEnabled(not is_project_running)
        self.ui.hdr_mertens_button.setEnabled(not is_project_running)
        self.ui.hdr_robertson_button.setEnabled(not is_project_running)

        self.ui.crop_slider.setEnabled(not is_project_running)

        self.ui.base_tv_input.setEnabled(not is_project_running)
        self.ui.hdr_count_input.setEnabled(not is_project_running)
        self.ui.hdr_ev_input.setEnabled(not is_project_running)

        self.ui.contrast_slider.setEnabled(not is_project_running)
        self.ui.exposure_slider.setEnabled(not is_project_running)
        self.ui.saturation_slider.setEnabled(not is_project_running)

        self.ui.start_button.setEnabled(is_system_ready and not is_project_running)
        self.ui.pause_button.setEnabled(is_project_running)
        self.ui.stop_button.setEnabled(is_project_running)

        self.ui.liveview_checkbox.setEnabled(is_cam_connected)
        self.ui.hdr_preview_button.setEnabled(is_cam_connected and not is_project_running and not self.ui.liveview_checkbox.isChecked() and not self.camera.busy)

    def _update_project_progress(self):
        project = self.project_scheduler.current_project
        if project is None:
            return

        total = max(1, project.n_total_shots)
        finished = min(project.n_finished_shots, total)

        percent = int((finished / total) * 100)

        self.ui.progress_bar.setValue(percent)
        self.ui.progress_bar.setFormat(f"{finished}/{project.n_total_shots}")

        if self.project.started_at is not None and not project.finished:
            elapsed = int(time.time() - self.project.started_at)
            minutes = elapsed // 60
            seconds = elapsed % 60
            self.ui.time_label.setText(f"{minutes}:{seconds:02d} min")
    
    def _handle_project_dialogs(self):
        if not self.project:
            return
        
        if self.project.finished and not self.project.finish_confirmed:
            self.show_project_finished_dialog()
            self.project_scheduler.confirm_finish()
            
        if self.project.turnable and not self.project.turn_confirmed:
            self.show_rotate_dialog()
            self.project_scheduler.confirm_turn
    
    def update_ui(self):
        self._block_settings_while_running()
        self._update_status_bar()
        self._update_hardware_visuals()
        self._update_project_progress()  
        
        self._handle_project_dialogs()
        
    def update_preview(self):
        if self.camera.is_connected() and self.ui.liveview_checkbox.isChecked():
            self.preview = Image(data=self.camera.liveview_data)
            self.preview.crop(settings.app.image_crop)
            
            self.preview_bytes = None
                        
        elif self.preview_bytes:
            self.preview = Image(self.preview_bytes)
            self.preview.crop(settings.app.image_crop)
            
        if not self.camera.is_connected():
            self.preview = Image(Path("assets/NoSignal.jpg").read_bytes())
            self.preview_bytes = None
        
        if self.camera.is_connected() and not self.ui.liveview_checkbox.isChecked() and not self.preview_bytes:
            self.ui.image_label.setPixmap(QPixmap())
            return
        
        self.preview.downsample()
        
        pixmap = self.preview.get_pixmap()

        self._set_preview_pixmap(pixmap)
    ## Aktions-Auslöser ###########
    def _on_start_clicked(self):
        if not self.camera.is_connected() or not self.serial_device.is_connected():
            return
        
        if not self.camera_crane.nulled.is_set():
            return

        name = self.ui.name_input.text().strip()

        if not name:
            return self.show_invalid_dialog()
        
        if len(name) != 5:
            return self.show_invalid_dialog()
        
        try:
            int(str(name))
        except ValueError:
            return self.show_invalid_dialog()
        
        dst = Path(settings.process.destination_dir)

        project_dst = dst / name
        if project_dst.exists():
            result = self.show_destination_already_exists_dialog()
            if not result:
                return self.show_invalid_dialog()

        self.project = self.project_scheduler.create_project(name, dst)
        
        self.project_scheduler.start_project(self.project) #TODO: implementieren
        self._reset_progress_ui()
    
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
        self._reset_progress_ui()
    
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
                        logger.error("Bildaufnahme fehlgeschlagen", stack_info=True)

                    images.append(result.image)

                cv_images = []
                for image in images:                    
                    cv_img = image.get_cv2_image()
                    if cv_img is None:
                        logger.error("Bild konnte nicht dekodiert werden", stack_info=True)
                    cv_images.append(cv_img)

                if len(cv_images) == 0:
                    logger.error("Keine Bilder für Preview vorhanden", stack_info=True)

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
                    logger.error("HDR-Verarbeitung fehlgeschlagen", stack_info=True)

                preview_image = Image()
                preview_image.cv2_to_data(result_img)

                if not preview_image.data:
                    logger.error("preview konnte nicht codiert werden", stack_info=True)

                self.preview_bytes = preview_image.data

            except Exception as e:
                logger.error("Fehler bei HDR Preview", stack_info=True)

            finally:
                self.ui.hdr_preview_button.setEnabled(True)

        threading.Thread(target=worker, daemon=True).start()
        
    ## Dialog Helpers #############
    def show_invalid_dialog(self) -> bool:
        dlg = InvalidArticleNumberDialog()
        dlg.show()

        return dlg.exec()

    def show_rotate_dialog(self) -> bool:
        dlg = RotatePartDialog()
        dlg.show()

        return dlg.exec()

    def show_destination_already_exists_dialog(self) -> bool:
        dlg = DestinationAlreadyExistsDialog(self.ui.name_input.text())
        dlg.show()

        return dlg.exec()
    
    def show_project_finished_dialog(self) -> bool:
        dlg = ProjectFinishedDialog(self.project_scheduler.current_project.dir_destination)
        dlg.show()

        return dlg.exec()
    
    ## Setting Update #############
    def _on_base_tv_changed(self, text: str):
        value = _parse_float(text)
        if not value or value <= 0:
            return
        _set_and_save(settings.camera, "base_tv", value)


    def _on_hdr_ev_changed(self, value):
        _set_and_save(settings.camera, "hdr_ev", float(value))


    def _on_hdr_count_changed(self, value):
        if value % 2 == 0:
            return
        _set_and_save(settings.camera, "hdr_shot_count", int(value))
    
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
        
    ## Close Event ################
    def open_settings_folder(self):
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
            except Exception as e:
                logger.exception("Error stopping instance on closeEvent")

        super().closeEvent(event)
        
## Applikation starten ########
if __name__ == "__main__":
    try:
        app = QApplication(sys.argv)

        window = MainWindow()
        window.show()

        exit_code = app.exec()
        logger.info("Application exited with code %s", exit_code)
        sys.exit(exit_code)

    except Exception as e:
        logger.exception("Unhandled exception in app.py main")
        sys.exit(1)