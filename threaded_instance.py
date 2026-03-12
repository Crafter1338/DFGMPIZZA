from threading import Thread, Event

class ThreadedInstance(Thread):
    def __init__(self):
        super().__init__(daemon=True)

        self._stop_event = Event()
        self._pause_event = Event()
        self._pause_event.set()

    def stop(self):
        self._stop_event.set()
        self._pause_event.set()

    def shutdown(self):
        self.stop()
        self.join()

    def pause(self):
        self._pause_event.clear()

    def resume(self):
        self._pause_event.set()

    def is_stopped(self):
        return self._stop_event.is_set()

    def is_paused(self):
        return not self._pause_event.is_set()

    def wait_if_paused(self):
        self._pause_event.wait()