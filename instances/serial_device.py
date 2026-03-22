import time
from typing import *
import serial
from threading import Event, RLock

from application.settings import settings
from instances.threaded_instance import ThreadedInstance

from collections import deque
from concurrent.futures import Future

class SerialDevice(ThreadedInstance):
    def __init__(self):
        self.ser: Optional[serial.Serial] = None

        self.instruction_queue: Deque[Tuple[List[str], Future]] = deque()

        self.queue_lock = RLock()
        self.serial_lock = RLock()

        super().__init__()


    def connect(self):
        with self.serial_lock:
            if self.ser:
                self._disconnect()

            self.ser = serial.Serial(
                port=settings.serial.port,
                baudrate=settings.serial.baudrate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=settings.serial.timeout
            )

            if self.ser and self.ser.is_open:
                self.queue_instructions(_generate_connection_instructions()["SET"])
                return True
            
        return False

    def disconnect(self):
        with self.serial_lock:
            if self.ser:
                try:
                    self.ser.close()
                except Exception as e:
                    pass

            self.ser = None
            return True
        
        return False
    
    def tick(self):
        item = None

        with self.queue_lock:
            if self.instruction_queue:
                item = self.instruction_queue.popleft()

        if item is None:
            return

        instructions, future = item

        try:
            last_response = None

            for instruction in instructions:
                last_response = self.send_instruction(instruction)

            if not future.done():
                future.set_result(last_response)

        except Exception as e:
            with self.queue_lock:
                self.instruction_queue.appendleft((instructions, future))


    def queue_instructions(self, instructions: list[str]) -> Future:
        future = Future()
        with self.queue_lock:
            self.instruction_queue.append((instructions, future))

        return future
    
    def send_instruction(self, instruction: str) -> Optional[str]:
        try:
            if not self.is_connected(): return
            
            # Hex-String in Bytes
            with self.serial_lock:
                if not self.ser or not self.ser.is_open:
                    self._disconnect()
                    return None
    
                instruction_bytes = bytes.fromhex(instruction.replace(" ", ""))
                self.ser.write(instruction_bytes)
                self.ser.flush()

                response = self.ser.read(9)
                
            if response:
                return ' '.join(f"{b:02X}" for b in response)
            
            return None

        except serial.SerialException as e:
            self._disconnect()
            return None
            
        except Exception as e:
            self._disconnect()
            return None



##################################################################

def _instruction_to_bytes(instruction: str):
    return bytes.fromhex(instruction)

def _bytes_to_instruction(base_bytes: bytes, value_bytes: bytes, generate_cc: bool = True): # Konvertiere Adress Bytes + Wert Bytes zu gewohntem String Format
    if generate_cc:
        checksum = sum(base_bytes + value_bytes) % 256  
        return ' '.join(f"{b:02X}" for b in base_bytes + value_bytes + [checksum])

    return ' '.join(f"{b:02X}" for b in base_bytes + value_bytes)

def _value_to_bytes(value: int, factor: float): # Konvertiere Wert mit Faktor zu gewohntem String Format "WW WW WW WW"
    return [(round(value * factor) >> (8 * i)) & 0xFF for i in reversed(range(4))]

def _bytes_to_value(value_bytes: bytes, factor: float, signed: bool = False): # Konvertiere "WW WW WW WW" mit Faktor zu Wert
    return int.from_bytes(value_bytes, byteorder='big', signed=signed) / factor

def _retrieve_value_from_instruction(instruction: str, factor: float = 1.0, signed: bool = False): # Entnimm dem gewohntem String Format den Wert mit Faktor
    parts = instruction.split()
    return _bytes_to_value(bytes(int(b, 16) for b in parts[-5:-1]), factor, signed)

static_instructions = { # Serielle Instruktionen im gewohntem String Format
    "arm": {
        "up": ['02 01 00 00 00 10 C8 E0 BB'],
        "down": ['02 02 00 00 00 10 C8 E0 BC'],
        "end": ['02 03 00 00 00 00 00 00 05', '02 06 01 00 00 00 00 00 09'],
    },
    "table": {
        "left": ['01 01 00 00 00 00 C3 50 15'],
        "right": [
            '01 02 00 00 00 00 C3 50 16',
            '01 06 05 00 00 00 00 00 0C',
            '01 06 16 00 00 00 00 00 1D',
            '01 06 17 00 00 00 00 00 1E',
        ],
        "end": [
            '01 03 00 00 00 00 00 00 04',
            '01 06 01 00 00 00 00 00 08'
        ],
        "zero": [
            '01 05 01 00 00 00 00 00 07',
            '01 05 00 00 00 00 00 00 06',
            '01 06 01 00 00 00 00 00 08',
        ],
    }
}

def _generate_move_to_instructions(percentage: int):
    factor = 365000
    value_bytes = _value_to_bytes(percentage, factor)

    return {
        "factor": factor,
        "SET": [_bytes_to_instruction([0x02, 0x04, 0x00, 0x00], value_bytes)],
        "GET": ["02 06 01 00 00 00 00 00 09"],
        "ANSWER": [_bytes_to_instruction([0x0A, 0x02, 0x64, 0x06], value_bytes)],
    }

def _generate_rotate_by_instructions(angle: int):
    factor = (255975/90)
    value_bytes = _value_to_bytes(angle, factor)

    return {
        "factor": factor,
        "SET": [_bytes_to_instruction([0x01, 0x04, 0x01, 0x00], value_bytes)],
        "GET": [_bytes_to_instruction([0x01, 0x06, 0x01, 0x00], value_bytes)],
        "ANSWER": [_bytes_to_instruction([0x0A, 0x01, 0x64, 0x04], value_bytes)],
    }

def _generate_speed_instructions(percentage: int):
    value_bytes = _value_to_bytes(percentage, 1000)

    return {
        "SET": [_bytes_to_instruction([0x01, 0x05, 0x04, 0x00], value_bytes)],
    }

def _generate_accel_instructions(percentage: int):
    value_bytes_w = _value_to_bytes(percentage, 1000)
    value_bytes_x = _value_to_bytes(percentage, 300)
    value_bytes_y = _value_to_bytes(percentage, 500)

    return {
        "SET": [
            _bytes_to_instruction([0x01, 0x05, 0x05, 0x00], value_bytes_w),
            _bytes_to_instruction([0x01, 0x05, 0x05, 0x00], value_bytes_w),
            _bytes_to_instruction([0x01, 0x05, 0x16, 0x00], value_bytes_x),
            _bytes_to_instruction([0x01, 0x05, 0x17, 0x00], value_bytes_y),
            _bytes_to_instruction([0x01, 0x05, 0x11, 0x00], value_bytes_w),
            _bytes_to_instruction([0x01, 0x05, 0x18, 0x00], value_bytes_x),
            _bytes_to_instruction([0x01, 0x05, 0x19, 0x00], value_bytes_y),
        ],
    }

def _generate_connection_instructions(speed: int = 50, accel: int = 50):
    speed_instructions = _generate_speed_instructions(speed)["SET"]
    accel_instructions = _generate_accel_instructions(accel)["SET"]

    return {
        "SET": [ 
            "01 0A 34 02 00 00 00 00 41",
            "01 0A 35 02 00 00 00 00 42",
            *speed_instructions,
            *accel_instructions,
            "02 05 04 00 00 10 C8 E0 C3",
            "02 05 05 00 03 93 87 00 29",
            "01 0A 36 02 00 00 00 00 43",
            "01 0A 37 02 00 00 00 00 44",
            "01 05 06 00 00 00 00 64 70",
            "01 05 C8 00 00 00 00 64 32",
            "01 05 07 00 00 00 00 14 21",
            "03 05 04 00 00 03 0D 40 5C",
            "03 05 06 00 00 00 00 64 72",
            "03 05 C8 00 00 00 00 96 66",
            "02 05 04 00 00 10 C8 E0 C3",
            "02 05 06 00 00 00 00 32 3F",
            "02 05 C8 00 00 00 00 50 1F",
            "02 05 1B 00 02 43 FC 90 F3",
            "02 05 1C 00 00 00 00 00 23",
            "02 05 1D 00 00 00 00 00 24",
            "01 06 01 00 00 00 00 00 08",
            "02 06 01 00 00 00 00 00 09",
            "03 06 01 00 00 00 00 00 0A",
            "02 0F 00 02 00 00 00 00 13",
            *speed_instructions,
            *accel_instructions,
        ],
    }

##################################################################