import time
import logging
from threading import Event

logger = logging.getLogger(__name__)


class ReconnectingMixin:
    """
    Mixin für automatische Reconnect Logik.
    """

    reconnect_delay: float = 5.0
    _connected: bool = False
    _last_connect_attempt: float = 0.0

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._connected = False
        self._last_connect_attempt = 0.0

    ####

    def is_connected(self) -> bool:
        return self._connected

    ####

    def connect(self) -> bool:
        """
        Verbindung herstellen.
        
        Returns:
            True = erfolgreich verbunden
            False = fehlgeschlagen
        """
        return True

    def disconnect(self) -> bool:
        """
        Verbindung trennen.
        
        Returns:
            True = erfolgreich getrennt
            False = fehlgeschlagen
        """
        return True

    ####

    def ensure_connection(self) -> None:
        """
        Stellt sicher, dass eine Verbindung besteht.
        Führt ggf. Reconnect-Versuch aus (mit Delay).
        """

        if self._connected:
            return

        now = time.time()
        if now - self._last_connect_attempt < self.reconnect_delay:
            return

        self._last_connect_attempt = now

        try:
            success = self.connect()

            if success:
                self._connected = True
                logger.info("Verbunden: %s", self.__class__.__name__)
            else:
                self._connected = False
                logger.warning("Verbindung fehlgeschlagen: %s", self.__class__.__name__)

        except Exception:
            self._connected = False
            logger.exception("Fehler beim Verbinden: %s", self.__class__.__name__)

    def force_disconnect(self) -> None:
        """
        Erzwingt Disconnect und setzt Status zurück.
        """
        try:
            self.disconnect()
        except Exception:
            logger.exception("Fehler beim Disconnect: %s", self.__class__.__name__)
        finally:
            self._connected = False