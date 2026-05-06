import logging
import logging.handlers
from pathlib import Path
import os

import utility.paths as paths


def setup_logging(production: bool = False) -> Path:
    """
    Logging einrichten.
    
    Args:
        production: Wenn True, nur WARNING+ in der Konsole. DEBUG Details nur in Dateien.
    
    Returns:
        Path zum Logging-Verzeichnis
    """
    log_dir = paths.base_data_dir / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    
    if root.handlers:
        return log_dir
    
    formatter_detailed = logging.Formatter(
        '[%(asctime)s] %(levelname)-8s [%(name)s:%(funcName)s:%(lineno)d] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    formatter_simple = logging.Formatter(
        '%(levelname)-8s [%(name)s] %(message)s'
    )
    
    file_handler = logging.handlers.RotatingFileHandler(
        log_dir / "app.log",
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter_detailed)
    root.addHandler(file_handler)
    
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING if production else logging.INFO)
    console_handler.setFormatter(formatter_simple)
    root.addHandler(console_handler)
    
    error_handler = logging.handlers.RotatingFileHandler(
        log_dir / "errors.log",
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.WARNING)
    error_handler.setFormatter(formatter_detailed)
    root.addHandler(error_handler)
    
    return log_dir