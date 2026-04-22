import time

from instances.camera import Camera


camera = Camera()

camera.start()

start_time = time.time()
while not camera.is_stopped():
    time.sleep(0.5)
    print(f"läuft seit {time.time() - start_time}s")