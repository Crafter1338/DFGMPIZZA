import time

from core.classes.camera import Camera
from core.classes.camera_crane import CameraCrane
from core.classes.process_orchestrator import ProcessOrchestrator
from core.classes.serial_orchestrator import SerialOrchestrator
from core.classes.turn_table import TurnTable
from projectclasses.Project import Project

# TESTCODE um Basisfunktionalität zu überprüfen

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

time.sleep(60) # Null Zeit

if not serial_orchestrator.is_connected() or not camera.is_connected():
    print("System nicht verbunden. Bitte Verbindungen überprüfen.")
    exit(1)

project = Project("00000", "./results", camera)
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