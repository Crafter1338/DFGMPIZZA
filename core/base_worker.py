import logging
import time
from threading import Thread, Event
from utility.settings import settings

logger = logging.getLogger(__name__)


class BaseWorker(Thread):
    def __init__(self, name: str | None = None):
        super().__init__(daemon=True, name=name)

        self._stop = Event()
        self._pause = Event()
        self._pause.set()

        self._tick_sleep = 1 / settings.app.thread_refreshrate

        self._last_log = 0.0

        logger.debug("Worker initialisiert: %s", self.name)

    ####

    def stop(self):
        """Stoppt den Worker-Thread."""
        logger.info("Worker wird gestoppt: %s", self.name)
        self._stop.set()
        self._pause.set()

    def pause(self):
        """Pausiert die Ausführung des Workers."""
        logger.info("Worker pausiert: %s", self.name)
        self._pause.clear()

    def resume(self):
        """Setzt einen pausierten Worker fort."""
        logger.info("Worker wird fortgesetzt: %s", self.name)
        self._pause.set()

    def stopped(self) -> bool:
        """Prüft, ob der Worker gestoppt wurde."""
        return self._stop.is_set()

    def paused(self) -> bool:
        """Prüft, ob der Worker pausiert ist."""
        return not self._pause.is_set()

    def wait_if_paused(self):
        """Blockiert den Thread, solange er pausiert ist."""
        self._pause.wait()

    ####

    def loop(self):
        """Muss überschrieben werden."""
        raise NotImplementedError

    def on_start(self):
        """Wird einmal beim Start des Threads aufgerufen."""
        pass

    ####

    def run(self):
        """Hauptausführungsschleife des Threads."""
        logger.info("Worker gestartet: %s", self.name)

        try:
            self.on_start()
        except Exception:
            logger.exception("Fehler in on_start: %s", self.name)

        while not self.stopped():
            try:
                self.wait_if_paused()

                if self._tick_sleep:
                    time.sleep(self._tick_sleep)

                self.loop()

            except Exception:
                logger.exception("Fehler im Worker-Loop: %s", self.name)
                self._safe_throttle_log("loop_error")

        logger.info("Worker gestoppt: %s", self.name)

    ####

    def _safe_throttle_log(self, key: str, interval: float = 60.0):
        """
        Verhindert Log-Spam bei wiederkehrenden Fehlern.
        """
        now = time.time()
        if now - self._last_log > interval:
            logger.warning("Gedrosseltes Ereignis: %s (%s)", key, self.name)
            self._last_log = now