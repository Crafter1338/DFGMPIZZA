import math
import time

from core.classes.camera import Camera
from core.classes.camera_crane import CameraCrane
from core.classes.process_orchestrator import ProcessOrchestrator
from core.classes.serial_orchestrator import SerialOrchestrator
from core.classes.turn_table import TurnTable
from projectclasses.Project import Project
from utility import logging_config

# TESTCODE um Basisfunktionalität zu überprüfen

logging_config.setup_logging(False)

camera = Camera()

serial_orchestrator = SerialOrchestrator()
turn_table = TurnTable(serial_orchestrator)
camera_crane = CameraCrane(serial_orchestrator)

process_orchestrator = ProcessOrchestrator(camera, serial_orchestrator, camera_crane, turn_table)

camera.start()
serial_orchestrator.start()
turn_table.start()
camera_crane.start()
process_orchestrator.start()

print("Programm gestartet")

time.sleep(60) # Null Zeit

print("Programm genullt")

if not serial_orchestrator.is_connected() or not camera.is_connected():
    print("System nicht verbunden. Bitte Verbindungen überprüfen.")
    exit(1)

project = Project("05919", "./results", camera)
process_orchestrator.set_project(project)

input("System bereit. Drücken Sie Enter, um die Hauptschleife zu starten...")
project.start()

while True:
    time.sleep(1)
    
    if project.turnable and not project.turn_confirmed:
        print("Drehen Sie das Objekt und bestätigen Sie mit Enter...")
        input()
        project.turn_confirmed = True
        project.resume() # Projekt fortsetzen nach User Input
        print("Drehen bestätigt. Fortfahren mit dem Projekt...")
        
    if project.finished and not project.finish_confirmed:
        print("Projekt abgeschlossen. Bestätigen Sie mit Enter...")
        input()
        project.finish_confirmed = True
        print("Projekt vollständig abgeschlossen.")
        break
    
    project.calculate_estimated_time_remaining()
    print(f"{math.floor(project.estimated_time_remaining/60)} min {project.estimated_time_remaining%60} s")
    
    # TODO: Todo erledigen und instructions schreiben, Kamera Fokus muss auf Einzelfeld sein, muss manuell angesteuert sein
    # TODO: Device busy error kann immernoch passieren
    # TODO: Wrap edsdk call function um jeden call abzusichern vor device busy (5s später selben befehl nochmal issuen) und internal error usw
    # TODO: durch AF modes switchen wenn AF fehlschlägt, statt wieder in queue zu packen
    # Googeln wie das in der Industrie gemacht wird