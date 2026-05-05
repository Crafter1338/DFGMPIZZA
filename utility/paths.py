import sys
import os
from pathlib import Path

# Allgemeine Funktionen für Pfadmanagement

def get_app_root() -> Path:
    """Gibt das Verzeichnis zurück, in dem die App-Dateien liegen (z.B. für Ressourcen)."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    
    return Path(__file__).resolve().parent.parent

def get_user_data_dir(app_name: str) -> Path:
    """Gibt den Pfad zum Speichern von Benutzerdaten zurück (z.B. Einstellungen)."""
    if os.name == "nt":
        base = Path(os.getenv("APPDATA", Path.home() / "AppData/Roaming")) # Windows
    else:
        base = Path.home() / ".local/share" # Linux/MacOS
    
    path = base / app_name
    path.mkdir(parents=True, exist_ok=True)
    
    return path

app_name = "PIZZA-DFGM"
base_data_dir = get_user_data_dir(app_name)

settings_file = base_data_dir / "settings.json"

def resolve_path(input_path: str | Path) -> Path:
    """
    Pfadlogik:
        - Absolut: Wird so gelassen.
        - Relativ: Wird in das base_data_dir gelegt.
    """
    
    p = Path(input_path)
    if p.is_absolute():
        return p
    
    return base_data_dir / p