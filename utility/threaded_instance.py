import logging
from threading import Thread, Event
import time

from utility.settings import settings

logger = logging.getLogger(__name__)

class ThreadedInstance(Thread):
    def __init__(self):
        super().__init__(daemon=True)

        self._last_connect = 0

        self._connected_event = Event()
        self._stop_event = Event()
        self._pause_event = Event()

        self._pause_event.set()


    def stop(self):
        self._stop_event.set()
        self._pause_event.set()
        self._connected_event.clear()

    def pause(self):
        self._pause_event.clear()

    def resume(self):
        self._pause_event.set()


    def is_connected(self):
        return self._connected_event.is_set()

    def is_stopped(self):
        return self._stop_event.is_set()

    def is_paused(self):
        return not self._pause_event.is_set()
    
    def wait_if_paused(self):
        self._pause_event.wait()

    
    def _connect(self):
        try:
            if self.connect():
                self._connected_event.set()
        except Exception as e:
            self._connected_event.clear()

        self._last_connect = time.time()

    def _disconnect(self):
        try:
            self.disconnect()
            self._connected_event.clear()
        except Exception as e:
            logger.exception("ThreadedInstance._disconnect error")
            return

    def connect(self) -> bool: # Muss von Unterklasse definiert werden
        self._connected_event.set()
        return True

    def disconnect(self) -> bool: # Muss von Unterklasse definiert werden
        self._connected_event.clear()
        return True

    def tick(self): # Muss von Unterklasse definiert werden
        return

    def on_start(self): # Muss von Unterklasse definiert werden
        return

    def run(self):
        logger.info("STARTING: %s", self)
        try:
            self.on_start()
        except Exception as e:
            logger.exception("ThreadedInstance.on_start error")
            
        while not self.is_stopped():
            try:
                self.wait_if_paused()

                time.sleep(1 / settings.app.thread_refreshrate)

                if not self.is_connected() and time.time() - self._last_connect > settings.app.reconnect_delay:
                    self._connect()
                    continue

                self.tick()

            except Exception as e:
                logger.exception("ThreadedInstance.run error")
                self._disconnect()
                