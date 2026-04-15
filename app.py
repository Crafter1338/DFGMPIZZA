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

from ui.aspect_ratio_movie import AspectRatioMovieLabel

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

from functools import wraps
###############################
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QDialog,
)
from PySide6.QtCore import QTimer, QUrl
from PySide6.QtGui import QColor, QDesktopServices, QMovie, QPixmap

from ui.aspect_ratio_label import AspectRatioLabel
from ui.ui_mainwindow import Ui_MainWindow

from ui.ui_destinationalreadyexists import Ui_Dialog as Ui_D_Dialog
from ui.ui_rotatepart import Ui_Dialog as Ui_R_Dialog
from ui.ui_invalidarticle import Ui_Dialog as Ui_I_Dialog
from ui.ui_projectfinished import Ui_Dialog as Ui_P_Dialog
from ui.spinner import WaitingSpinner
###############################
from utility.settings import settings
from utility import settings as settings_module

from instances.serial_device import SerialDevice
from instances.camera_crane import CameraCrane
from instances.turn_table import TurnTable

from instances.camera import Camera
import utility.file_processing as fp

from instances.project_scheduler import Project, ProjectScheduler
###############################
from utility.datastructures import Image

## Helpers ####################
def _parse_float(text: str):
    try:
        return float(text.strip().replace(",", "."))
    except ValueError:
        return None

def _clamp01(value: float):
    return min(max(value, 0), 1)

def _set_and_save(obj, attr: str, value):
    setattr(obj, attr, value)
    settings.save()

def cameraready(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        if self.camera is None:
            #logger.warning("Camera missing")
            return None

        if not self.camera.is_connected():
            #logger.debug("Camera not connected")
            return None

        return func(self, *args, **kwargs)
    return wrapper

def mechanicsready(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        if not all([self.serial_device, self.camera_crane, self.turn_table]):
            #logger.warning("Mechanics missing")
            return None

        if not self.serial_device.is_connected():
            #logger.debug("Serial not connected")
            return None

        if not self.camera_crane.nulled.is_set():
            #logger.debug("Crane not nulled")
            return None

        if not self.turn_table.nulled.is_set():
            #logger.debug("Turntable not nulled")
            return None

        return func(self, *args, **kwargs)
    return wrapper

def systemready(func):
    @wraps(func)
    @cameraready
    @mechanicsready
    def wrapper(self, *args, **kwargs):
        return func(self, *args, **kwargs)
    return wrapper
    

## Dialoge / Pop-Ups ##########
class RotatePartDialog(QDialog):
    def __init__(self):
        super().__init__()

        self.ui = Ui_R_Dialog()
        self.ui.setupUi(self)

        self._replace_movie_label()

        self.movie = QMovie(str(settings_module.resource_path("assets/rotate_part.gif")))

        if self.movie.isValid():
            self.ui.label_movie.setMovie(self.movie)  # now uses YOUR method
        else:
            print("Failed to load GIF")

    def _replace_movie_label(self):
        layout = self.ui.verticalLayout

        old_label = self.ui.label_movie

        new_label = AspectRatioMovieLabel(self, aspect_ratio=16/9)
        new_label.setObjectName("label_movie")

        index = layout.indexOf(old_label)
        layout.removeWidget(old_label)
        old_label.deleteLater()

        layout.insertWidget(index, new_label)

        self.ui.label_movie = new_label
            
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
        
        self.preview_spinner: Optional[WaitingSpinner] = None
        self.is_generating_hdr_preview = False
        
        self.is_moving_by_buttons = False
        
        self.last_preview_bytes: Optional[bytes] = None
        self.last_preview_crop: Optional[float] = None
        
        self._replace_image_label()
        self._insert_spinner()
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
    def _insert_spinner(self): # Drehteil damit man während HDR Preview nicht ganz alleine ist
        self.preview_spinner = WaitingSpinner(self.ui.image_label_right, True, True, radius=30, color=QColor(255,255,255), line_width=4, line_length=14)
        self.preview_spinner.stop()
    
    def _replace_image_label(self): # Sorgt dafür, dass jedes Image im Preview auch wirklich 16:9 ist
        for old_label in [self.ui.image_label_left, self.ui.image_label_right]:
            parent_layout = self.ui.horizontalLayout

            new_label = AspectRatioLabel(self.centralWidget(), aspect_ratio = 16 / 9)
            new_label.setObjectName(old_label.objectName())

            index = parent_layout.indexOf(old_label)
            parent_layout.removeWidget(old_label)
            old_label.deleteLater()

            parent_layout.insertWidget(index, new_label)
            setattr(self.ui, old_label.objectName(), new_label)

    def _init_ui_from_settings(self): # Stellt das UI von den Settings ein
        self.ui.base_tv_slider.setValue(int(settings.camera.base_tv* 100))
        self.ui.hdr_ev_input.setValue(settings.camera.hdr_ev)
        self.ui.hdr_count_input.setValue(settings.camera.hdr_shot_count)

        self.ui.crop_slider.setValue(int(round(settings.app.image_crop * 100)))

        self.ui.single_picture_button.setChecked((not settings.camera.use_drago and not settings.camera.use_robertson))
        self.ui.hdr_drago_button.setChecked(settings.camera.use_drago)
        self.ui.hdr_robertson_button.setChecked(settings.camera.use_robertson)

        self._reset_progress_ui()

    def _connect_ui(self): # Verbindet das UI mit den Settings
        self.ui.base_tv_slider.sliderReleased.connect(self._on_base_tv_changed)
        
        self.ui.hdr_ev_input.valueChanged.connect(self._on_hdr_ev_changed)
        self.ui.hdr_count_input.valueChanged.connect(self._on_hdr_count_changed)

        self.ui.crop_slider.sliderMoved.connect(self._on_crop_change)
        self.ui.crop_slider.sliderReleased.connect(self._on_crop_changed)

        self.ui.single_picture_button.clicked.connect(self._on_radio_button_changed)
        self.ui.hdr_drago_button.clicked.connect(self._on_radio_button_changed)
        self.ui.hdr_robertson_button.clicked.connect(self._on_radio_button_changed)

        self.ui.start_button.clicked.connect(self._on_start_clicked)
        self.ui.pause_button.clicked.connect(self._on_pause_clicked)
        self.ui.stop_button.clicked.connect(self._on_stop_clicked)

        self.ui.hdr_preview_button.clicked.connect(self._on_hdr_preview_clicked)

        self.ui.settings_button.clicked.connect(self.open_settings_folder)
        
        self.ui.move_arm_to_0.clicked.connect(self._on_0_press)
        self.ui.move_arm_to_50.clicked.connect(self._on_45_press)
        self.ui.pushButton.clicked.connect(self._on_85_press)
        
    def _set_preview_pixmap(self, pixmap: QPixmap):
        if pixmap and not pixmap.isNull():
            self.ui.image_label_right.setPixmap(pixmap)

    def _set_liveview_pixmap(self, pixmap: QPixmap):
        if pixmap and not pixmap.isNull():
            self.ui.image_label_left.setPixmap(pixmap)

    def _reset_progress_ui(self):
        self.ui.progress_bar.setRange(0, 100)
        self.ui.progress_bar.setValue(0)
        self.ui.progress_bar.setFormat("0/0")
        self.ui.time_label.setText("0:00 min")
        self.ui.pause_button.setText("Pause")
        
    ## Update UI ##################
    @systemready
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
        is_mechanics_ready = is_serial_connected and self.camera_crane.nulled.is_set() and self.turn_table.nulled.is_set()

        self.ui.name_input.setEnabled(is_system_ready and not is_project_running)

        self.ui.single_picture_button.setEnabled(not is_project_running and not self.is_generating_hdr_preview)
        self.ui.hdr_drago_button.setEnabled(not is_project_running and not self.is_generating_hdr_preview)
        self.ui.hdr_robertson_button.setEnabled(not is_project_running and not self.is_generating_hdr_preview)

        self.ui.crop_slider.setEnabled(not is_project_running and not self.is_generating_hdr_preview)

        self.ui.base_tv_input.setEnabled(not is_project_running and not self.is_generating_hdr_preview)
        self.ui.hdr_count_input.setEnabled(not is_project_running and not self.is_generating_hdr_preview and not self.ui.single_picture_button.isChecked())
        self.ui.hdr_ev_input.setEnabled(not is_project_running and not self.is_generating_hdr_preview and not self.ui.single_picture_button.isChecked())

        self.ui.start_button.setEnabled(is_system_ready and not is_project_running and not self.is_generating_hdr_preview and not self.is_moving_by_buttons)
        self.ui.pause_button.setEnabled(is_project_running and not self.is_generating_hdr_preview and not self.is_moving_by_buttons)
        self.ui.stop_button.setEnabled(is_project_running and not self.is_generating_hdr_preview and not self.is_moving_by_buttons)

        self.ui.hdr_preview_button.setEnabled(is_cam_connected and not is_project_running and not self.camera.busy and not self.is_generating_hdr_preview and not self.ui.single_picture_button.isChecked())

        self.ui.move_arm_to_0.setEnabled(is_mechanics_ready and not is_project_running and not self.is_generating_hdr_preview and not self.is_moving_by_buttons)
        self.ui.move_arm_to_50.setEnabled(is_mechanics_ready and not is_project_running and not self.is_generating_hdr_preview and not self.is_moving_by_buttons)

    @systemready
    def _update_project_progress(self):
        if self.camera_crane is not None and self.camera_crane.is_nulling:
            remaining = int(self.camera_crane.nulling_till - time.time())
            minutes = elapsed // 60
            seconds = elapsed % 60
            self.ui.time_label.setText(f"Noch {minutes:02d}:{seconds:02d} min")
            
        try:
            if self.project is None:
                self._reset_progress_ui()
                return
            
            if self.project_scheduler.current_project is None:
                self.project = None
                self._reset_progress_ui()
                return
            
            if not self.project_scheduler.is_project_running() and (self.project is not None and not self.project.finished):
                self.statusBar().showMessage(self.project.error or f"Projekt {self.project.name} fehlgeschlagen")
                self._on_stop_clicked()

            total = max(1, self.project.n_total_shots)
            finished = min(self.project.n_finished_shots, total)

            percent = int((finished / total) * 100)

            self.ui.progress_bar.setValue(percent)
            self.ui.progress_bar.setFormat(f"{finished}/{self.project.n_total_shots}")

            if self.project.started_at is not None and not self.project.finished:
                elapsed = int(time.time() - self.project.started_at)
                minutes = elapsed // 60
                seconds = elapsed % 60
                self.ui.time_label.setText(f"{minutes}:{seconds:02d} min")
        except:
            self.project = self.project_scheduler.current_project
    
    def _handle_project_dialogs(self):
        if not self.project:
            return
        
        if self.project.finished and not self.project.finish_confirmed:
            self.show_project_finished_dialog()
            self.project_scheduler.confirm_finish()
            self.statusBar().showMessage(f"Projekt {self.project.name} erfolgreich abgeschlossen")
            
            self._reset_progress_ui()
            self.project = None
            
            return
            
        if self.project.turnable and not self.project.turn_confirmed:
            self.show_rotate_dialog()
            self.project_scheduler.confirm_turn()
            
            return
    
    def update_ui(self):
        self._block_settings_while_running()
        self._update_status_bar()
        self._update_hardware_visuals()
        self._update_project_progress()
        
        self._handle_project_dialogs()
        
    def update_preview(self): #TODO: Rework
        #if self.camera.is_connected() and self.ui.liveview_checkbox.isChecked(): # Liveview muss nicht gesamplet werden weil sowieso klein
        #    self.preview = Image(data=self.camera.liveview_data)
        #    self.preview.crop(settings.app.image_crop)
        #    
        #    self.preview_bytes = None
        #                
        #elif self.preview_bytes != None:
        #    if (self.last_preview_bytes != None and self.last_preview_bytes == self.preview_bytes) and (self.last_preview_crop != None and self.last_preview_crop == settings.app.image_crop):
        #        return # Wenn nichts am Bild geändert wurde, nicht erneut croppen und samplen
        #    
        #    self.preview = Image(self.preview_bytes)
        #    self.preview.crop(settings.app.image_crop)
        #    self.preview.downsample()
        #    
        #    self.last_preview_bytes = self.preview_bytes
        #    self.last_preview_crop = settings.app.image_crop
            
        if not self.camera.is_connected(): # Wenn Kamera nicht verbunden, anzeigen
            self.preview = Image(Path(settings_module.resource_path("assets/NoSignal.jpg")).read_bytes())
            self.preview_bytes = None

        #if self.camera.is_connected() and not self.ui.liveview_checkbox.isChecked() and not self.preview_bytes: # Leeres Bild
            #self.ui.image_label.setPixmap(QPixmap())
        #    return
        
        if not self.preview:
            return
        
        pixmap = self.preview.get_pixmap()

        self._set_preview_pixmap(pixmap)
        
    ## Aktions-Auslöser ###########
    @systemready
    def _on_start_clicked(self):
        name = self.ui.name_input.text().strip()

        if not name:
            return self.show_invalid_dialog()
        
        if len(name) != 5:
            return self.show_invalid_dialog()

        try:
            int(str(name))
        except ValueError:
            return self.show_invalid_dialog()
        
        self.statusBar().showMessage(f"Projekt {name} gestartet")
        
        dst = Path(settings.process.destination_dir)

        project_dst = dst / name
        if project_dst.exists():
            result = self.show_destination_already_exists_dialog()
            if not result:
                return self.show_invalid_dialog()

        self.project = self.project_scheduler.create_project(name, dst)
        
        self.project_scheduler.start_project(self.project)
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
        self.project = None
    
    @cameraready
    def _on_hdr_preview_clicked(self):
        self.is_generating_hdr_preview = True
        self.preview_spinner.start()
        self.preview_bytes = None

        def worker():
            try:
                if not self.camera.is_connected():
                    return
                
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

                elif settings.camera.use_drago:
                    exposure_times = [payload.tv for payload in payloads]
                    
                    result_img = fp.hdr_merge_drago_buffer(
                        images=cv_images,
                        exposure_times=exposure_times,
                        gamma=settings.camera.tonemap_gamma
                    )

                elif settings.camera.use_robertson:
                    exposure_times = [payload.tv for payload in payloads]
                    
                    result_img = fp.hdr_merge_robertson_buffer(
                        images=cv_images,
                        exposure_times=exposure_times,
                        gamma=settings.camera.tonemap_gamma
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
                self.preview_spinner.stop()
                self.is_generating_hdr_preview = False

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
    def _on_base_tv_changed(self):
        if self.ui.base_tv_slider.value() is None: 
            return 
    
        value = _parse_float(self.ui.base_tv_slider.value()/100)
        
        if value is None or value <= 0:
            return
        
        if self.camera is not None and self.camera.is_connected():
            self.camera.enqueue_property_change(settings.camera.iso, settings.camera.av, value) 
        
        _set_and_save(settings.camera, "base_tv", value)


    def _on_hdr_ev_changed(self):
        if self.ui.hdr_ev_input.value() is None: 
            return 
        
        _set_and_save(settings.camera, "hdr_ev", self.ui.hdr_ev_input.value())


    def _on_hdr_count_changed(self):
        if self.ui.hdr_count_input.value() is None: 
            return 
        
        if self.ui.hdr_count_input.value() % 2 == 0:
            return
        _set_and_save(settings.camera, "hdr_shot_count", self.ui.hdr_count_input.value())
    
    def _on_crop_change(self):
        settings.app.image_crop = min(max(self.ui.crop_slider.value() / 100, 0), 1)

    def _on_crop_changed(self):
        settings.app.image_crop = min(max(self.ui.crop_slider.value() / 100, 0), 1)
        settings.save()

    def _on_radio_button_changed(self):
        settings.camera.use_drago   = self.ui.hdr_drago_button.isChecked() and not self.ui.single_picture_button.isChecked()
        settings.camera.use_robertson = self.ui.hdr_robertson_button.isChecked() and not self.ui.single_picture_button.isChecked()
        settings.save()
        
    @mechanicsready
    def _on_85_press(self):
        def worker():
            try:
                self.is_moving_by_buttons = True
                self.camera_crane.move_to(0.5) # TODO: Cameracrane auf Winkel ändern
                
                self.camera_crane.moved.wait()
            finally:
                self.is_moving_by_buttons = False
                
        threading.Thread(target=worker, daemon=True).start()
        
    @mechanicsready
    def _on_45_press(self):
        def worker():
            try:
                self.is_moving_by_buttons = True
                self.camera_crane.move_to(0.5)  # TODO: Cameracrane auf Winkel ändern
                
                self.camera_crane.moved.wait()
            finally:
                self.is_moving_by_buttons = False
                
        threading.Thread(target=worker, daemon=True).start()
    
    @mechanicsready
    def _on_0_press(self):
        def worker():
            try:
                self.is_moving_by_buttons = True
                self.camera_crane.move_to(0)   # TODO: Cameracrane auf Winkel ändern
                
                self.camera_crane.moved.wait()
            finally:
                self.is_moving_by_buttons = False
                
        threading.Thread(target=worker, daemon=True).start()
        
    ## Close Event ################
    def open_settings_folder(self):
        settings_path = settings_module.file
        settings_path = settings_path.resolve()

        if settings_path.exists():
            if sys.platform == "win32":
                subprocess.Popen(["explorer", "/select,", str(settings_path)])
            else:
                QDesktopServices.openUrl(QUrl.fromLocalFile(str(settings_path.parent)))
        else:
            logger.debug(f"Settings-Datei nicht gefunden: {settings_path}")
            
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