from functools import wraps

def MechanicsReady(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        if not all([self.serial_orchestrator, self.camera_crane, self.turn_table]):
            return None

        if not self.serial_orchestrator.is_connected():
            return None

        if not self.camera_crane.nulled.is_set():
            return None

        if not self.turn_table.nulled.is_set():
            return None

        return func(self, *args, **kwargs)
    return wrapper

def ArmReady(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        if not all([self.serial_orchestrator, self.camera_crane]):
            return None

        if not self.serial_orchestrator.is_connected():
            return None

        if not self.camera_crane.nulled.is_set():
            return None

        return func(self, *args, **kwargs)
    return wrapper

def TableReady(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        if not all([self.serial_orchestrator, self.turn_table]):
            return None

        if not self.serial_orchestrator.is_connected():
            return None

        if not self.turn_table.nulled.is_set():
            return None

        return func(self, *args, **kwargs)
    return wrapper