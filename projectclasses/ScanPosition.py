from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
from venv import logger

from projectclasses.Image import Image
from projectclasses.ShotPayload import ShotPayload
from utility.paths import resolve_path
from utility.settings import settings
from utility.file_processing import crop_image_buffer, flip_image_buffer
from utility.image_processing import hdr_merge_drago_buffer

@dataclass
class ScanPosition:
    x_pos: float
    y_pos: float
    
    x_name: str
    y_name: str
    
    flipped: bool
    
    image_payloads: list[ShotPayload] = field(default_factory=list)
    images: list[Image] = field(default_factory=list)

    final_image: Optional[Image] = None
    
    current_shot_indx: int = 0
    
    finished: bool = False
    
    def check_if_finished(self) -> bool:
        return self.current_shot_indx >= len(self.image_payloads)
    
    def finish(self, project):
        '''
        Eine Methode um alles zu verarbeiten, sobald alle Bilder für diese ScanPosition aufgenommen wurden.
        Andere Methoden müssen nicht gecallt werden.
        Sollte gethreadedt werden, da die Bildverarbeitung eine Weile dauern kann, damit nicht der Hauptthread blockiert wird
        '''
        if not self.check_if_finished():
            return
        
        if len(self.images) == 0:
            return
        
        if len(self.images) != len(self.image_payloads):
            logger.warning(f"ScanPosition at ({self.x_name}, {self.y_name}) has mismatching number of images and payloads")
            return
        
        self.process_images()
        
        if self.final_image is None:
            logger.warning(f"ScanPosition at ({self.x_name}, {self.y_name}) failed to process images")
            return
        
        self.images.clear()
        self.image_payloads.clear()
        
        self.save_final_image(project.dir_destination)
        
        self.finished = True
        
    def process_images(self): # Prozessierung der HDR Bilder (und crop + flip), pasiert in thread während tick()
        try:
            cv_images: list = []

            for image in self.images:
                cv_img = image.get_cv2_image()
                if cv_img is None:
                    return False
                cv_images.append(cv_img)

            if len(cv_images) == 0:
                return False

            result = None

            if len(cv_images) == 1: # Einzelbild
                result = cv_images[0].copy()
            
            else:
                exposure_times = [payload.tv for payload in self.image_payloads]

                result = hdr_merge_drago_buffer(
                    images=cv_images,
                    exposure_times=exposure_times,
                    gamma=1.5,
                )

            if result is None:
                return False

            if settings.app.image_crop > 0: # Crop anwenden
                cropped = crop_image_buffer(result, settings.app.image_crop)
                if cropped is None:
                    return False
                result = cropped

            if self.flipped: # Flip anwenden für Bilder "von unten"
                flipped = flip_image_buffer(result)
                if flipped is None:
                    return False
                result = flipped

            self.final_image = Image()
            self.final_image.cv2_to_data(result)
        except Exception as e:
            logger.exception("ScanPosition.process_images error")
            
    def save_final_image(self, project_dir: Path): # Speichert das Bild im Projekt dir
        if self.final_image is None:
            return False
        
        project_dir = resolve_path(project_dir)

        row = int(self.y_name)
        col = int(self.x_name)

        filename = f"DFGM_R{row:02d}_C{col:02d}.jpg" # Namenformat
        final_dst = project_dir / filename

        self.final_image.save_as_file(final_dst)

        if settings.process.create_previews:
            preview_dst = project_dir / "preview" / filename
            self.final_image.save_preview(preview_dst) # Preview mit gleichem Namen in /preview speichern (Größe in settings.json gecapped)

        return True
            