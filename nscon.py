#!/usr/bin/env python3

from concurrent.futures import ThreadPoolExecutor, Future
from dataclasses import dataclass, field
import signal
import struct
import os
from typing import Dict, List


SPI_ROM_DATA: Dict[int, bytes] = {
    0x60: bytes([
        0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff,
        0xff, 0xff, 0x03, 0xa0, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0x02, 0xff, 0xff, 0xff, 0xff,
        0xf0, 0xff, 0x89, 0x00, 0xf0, 0x01, 0x00, 0x40, 0x00, 0x40, 0x00, 0x40, 0xf9, 0xff, 0x06, 0x00,
        0x09, 0x00, 0xe7, 0x3b, 0xe7, 0x3b, 0xe7, 0x3b, 0xff, 0xff, 0xff, 0xff, 0xff, 0xba, 0x15, 0x62,
        0x11, 0xb8, 0x7f, 0x29, 0x06, 0x5b, 0xff, 0xe7, 0x7e, 0x0e, 0x36, 0x56, 0x9e, 0x85, 0x60, 0xff,
        0x32, 0x32, 0x32, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff,
        0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff,
        0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff,
        0x50, 0xfd, 0x00, 0x00, 0xc6, 0x0f, 0x0f, 0x30, 0x61, 0x96, 0x30, 0xf3, 0xd4, 0x14, 0x54, 0x41,
        0x15, 0x54, 0xc7, 0x79, 0x9c, 0x33, 0x36, 0x63, 0x0f, 0x30, 0x61, 0x96, 0x30, 0xf3, 0xd4, 0x14,
        0x54, 0x41, 0x15, 0x54, 0xc7, 0x79, 0x9c, 0x33, 0x36, 0x63, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff,
    ]),
    0x80: bytes([
        0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff,
        0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff,
        0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xb2, 0xa1, 0xf6, 0x00, 0x1b, 0x00, 0x08, 0x02, 0x00, 0x40, 
        0x00, 0x40, 0x00, 0x40, 0x2e, 0x00, 0xda, 0xff, 0xcf, 0xff, 0x3b, 0x34, 0x3b, 0x34, 0x3b, 0x34,
    ]),
}


@dataclass
class Dpad:
    Up: int = field(default=0, init=False)
    Down: int = field(default=0, init=False)
    Left: int = field(default=0, init=False)
    Right: int = field(default=0, init=False)


@dataclass
class Button:
    A: int = field(default=0, init=False)
    B: int = field(default=0, init=False)
    X: int = field(default=0, init=False)
    Y: int = field(default=0, init=False)
    R: int = field(default=0, init=False)
    ZR: int = field(default=0, init=False)
    L: int = field(default=0, init=False)
    ZL: int = field(default=0, init=False)
    Home: int = field(default=0, init=False)
    Plus: int = field(default=0, init=False)
    Minus: int = field(default=0, init=False)
    Capture: int = field(default=0, init=False)


@dataclass
class Stick_struct:
    X: int = field(default=0x800, init=False)
    Y: int = field(default=0x800, init=False)
    Press: int = field(default=0, init=False)


@dataclass
class Stick:
    Left: Stick_struct = field(default=Stick_struct(), init=False)
    Right: Stick_struct = field(default=Stick_struct(), init=False)


@dataclass
class Sensor_struct:
    X: int = field(default=0, init=False)
    Y: int = field(default=0, init=False)
    Z: int = field(default=0, init=False)
    Sensitivity: float = field(default=1.0, init=False)


@dataclass
class Sensor:
    Accel: Sensor_struct = field(default=Sensor_struct(), init=False)
    Gyro: Sensor_struct = field(default=Sensor_struct(), init=False)


@dataclass
class ControllerInput:
    Dpad: Dpad = field(default=Dpad(), init=False)
    Button: Button = field(default=Button(), init=False)
    Stick: Stick = field(default=Stick(), init=False)
    Sensor: Sensor = field(default=Sensor(), init=False)


class Controller:
    path: str
    fp: str = None
    count: int = 0
    stopCounter: bool = True
    stopInput: bool = True
    stopCommunicate: bool = True
    Input: ControllerInput = ControllerInput()
    LogLevel: int = 0
    executor: ThreadPoolExecutor = ThreadPoolExecutor()
    future: Future = None
    ReportSec: int = 0.015

    def __init__(self, path) -> None:
        self.path = path

    def Close(self):
        if self.fp == None:
            return

        self.stopCounter = True
        self.stopInput = True
        signal.setitimer(signal.ITIMER_REAL, 0, 0)
        self.stopCommunicate = True

        os.close(self.fp)
        self.fp = None

    def Disconnect(self):
        buf: bytearray = bytearray(self.getInputBuffer() + bytes([0x80, 0x30]))
        self.write(0x21, self.count, buf)
        buf[10] = 0x0a
        self.write(0x21, self.count, buf)
        buf[10] = 0x09
        self.write(0x21, self.count, buf)

    def startTicker(self):
        tick: int = 0

        def tickScheduler(arg1, arg2):
            nonlocal tick
            tick += 1
            self.Counter()
            if tick % 3 == 0:
                self.InputReport()
                tick -= 3

        signal.signal(signal.SIGALRM, tickScheduler)
        signal.setitimer(signal.ITIMER_REAL, 0.005, 0.005)

    def Counter(self):
        if not self.stopCounter:
            self.count = (self.count + 1) % 256

    def InputReport(self):
        if not self.stopInput:
            self.write(0x30, self.count, self.getInputBuffer() + self.getSensorBuffer())

    def getInputBuffer(self) -> bytes:
        left = (bitInput(self.Input.Button.Y, 0) | bitInput(self.Input.Button.X, 1) |
                bitInput(self.Input.Button.B, 2) | bitInput(self.Input.Button.A, 3) |
                bitInput(self.Input.Button.R, 6) | bitInput(self.Input.Button.ZR, 7))

        center = (bitInput(self.Input.Button.Minus, 0) | bitInput(self.Input.Button.Plus, 1) |
                  bitInput(self.Input.Stick.Right.Press, 2) | bitInput(self.Input.Stick.Left.Press, 3) |
                  bitInput(self.Input.Button.Home, 4) | bitInput(self.Input.Button.Capture, 5))

        right = (bitInput(self.Input.Dpad.Down, 0) | bitInput(self.Input.Dpad.Up, 1) |
                 bitInput(self.Input.Dpad.Right, 2) | bitInput(self.Input.Dpad.Left, 3) |
                 bitInput(self.Input.Button.L, 6) | bitInput(self.Input.Button.ZL, 7))

        lx = self.Input.Stick.Left.X
        ly = self.Input.Stick.Left.Y << 12
        rx = self.Input.Stick.Right.X
        ry = self.Input.Stick.Right.Y << 12

        leftStick = int.to_bytes((ly | lx), 3, 'little')
        rightStick = int.to_bytes((ry | rx), 3, 'little')

        return struct.pack('B BBB 3s 3s B', 0x81, left, center, right,
                           leftStick, rightStick, 0x00)

    def getSensorBuffer(self) -> bytes:
        accelx = self.Input.Sensor.Accel.X & 0xFFFF
        accely = self.Input.Sensor.Accel.Y & 0xFFFF
        accelz = self.Input.Sensor.Accel.Z & 0xFFFF

        dot_per_degree = self.Input.Sensor.Gyro.Sensitivity
        gyrox = Dot2DPS(self.Input.Sensor.Gyro.X, dot_per_degree, self.ReportSec) & 0xFFFF
        gyroy = Dot2DPS(self.Input.Sensor.Gyro.Y, dot_per_degree, self.ReportSec) & 0xFFFF
        gyroz = Dot2DPS(self.Input.Sensor.Gyro.Z, dot_per_degree, self.ReportSec) & 0xFFFF

        sixaxis: bytes = b''.join([s.to_bytes(2, 'little')
                           for s in [accelx, accely, accelz, gyrox, gyroy, gyroz]])
        self.resetSensors()

        return sixaxis * 3

    def resetSensors(self):
        self.Input.Sensor.Accel.X = 0x0000
        self.Input.Sensor.Accel.Y = 0x0000
        self.Input.Sensor.Accel.Z = 0x0000
        self.Input.Sensor.Gyro.X  = 0x0000
        self.Input.Sensor.Gyro.Y  = 0x0000
        self.Input.Sensor.Gyro.Z  = 0x0000

    def uart(self, ack: bool, subCmd: int, data: bytes):
        ackByte = 0x00
        if ack:
            ackByte = 0x80
            if len(data):
                ackByte |= subCmd

        self.write(0x21, self.count,
                   self.getInputBuffer() + bytes([ackByte, subCmd]) + data)

    def write(self, ack: int, cmd: int, buf: bytes):
        data = bytes([ack, cmd]) + buf + bytes(62 - len(buf))
        if self.LogLevel > 4:
            print('<<<', data.hex())
        try:
            os.write(self.fp, data)
        except BlockingIOError:
            pass
        except:
            os._exit(1)

    def startConnect(self):
        print('---- ProCon Connection Started. ----')
        if self.fp != None:
            return

        try:
            self.fp = os.open(self.path, os.O_RDWR | os.O_NONBLOCK)
        except:
            return

        self.stopCounter = False
        self.stopCommunicate = False

        self.startTicker()

        def Connect(self):
            buf: bytes = bytes(128)

            while (not self.stopCommunicate):
                try:
                    buf = os.read(self.fp, 128)
                    if self.LogLevel > 4:
                                print('>>>', buf.hex())
                    if buf[0] == 0x80:
                        if buf[1] == 0x01:
                            self.write(0x81, buf[1], bytes(
                                [0x00, 0x03, 0x00, 0x00, 0x5e, 0x00, 0x53, 0x5e]))
                        elif buf[1] in [0x02, 0x03]:
                            self.write(0x81, buf[1], bytes(0))
                        elif buf[1] == 0x04:
                            print('---- ProCon Input Report Started. ----')
                            self.stopInput = False
                        else:
                            print('>>>', buf.hex())
                    elif buf[0] == 0x01:
                        if buf[10] == 0x01:
                            self.uart(True, buf[10], bytes([0x03, 0x01]))
                        elif buf[10] == 0x02:
                            self.uart(True, buf[10], bytes(
                                [0x03, 0x48, 0x03, 0x02, 0x5e, 0x53, 0x00, 0x5e, 0x00, 0x00, 0x03, 0x01]))
                        elif buf[10] in [0x03, 0x08, 0x30, 0x38, 0x40, 0x41, 0x48]:
                            self.uart(True, buf[10], bytes(0))
                        elif buf[10] == 0x04:
                            self.uart(True, buf[10], bytes(0))
                        elif buf[10] == 0x10:
                            if buf[12] in SPI_ROM_DATA:
                                data = SPI_ROM_DATA[buf[12]]
                                self.uart(
                                    True, buf[10], buf[11:16] + data[buf[11]:(buf[11]+buf[15])])
                                if self.LogLevel > 1:
                                    print(
                                        f"Read SPI address: {buf[12]:02x}{buf[11]:02x}[{buf[15]}] {data[buf[11]:buf[11]+buf[15]]}")
                            else:
                                self.uart(False, buf[10], bytes(0))
                                if self.LogLevel > 1:
                                    print(
                                        f"Unknown SPI address: {buf[12]:02x}[{buf[15]}]")
                        elif buf[10] == 0x21:
                            self.uart(True, buf[10], bytes(
                                [0x01, 0x00, 0xff, 0x00, 0x03, 0x00, 0x05, 0x01]))
                        else:
                            if self.LogLevel > 1:
                                print(f"UART unknown request {buf[10]} {buf}")
                except BlockingIOError:
                    pass
                except:
                    os._exit(1)

        self.future = self.executor.submit(Connect, self)


def bitInput(input, offset: int) -> int:
    return 1 << offset if input else 0

def Dot2DPS(dot: int, dot_per_degree: float, psec: float) -> int:
    degree: float = dot / dot_per_degree
    dps:float = degree / psec
    dps_digit: int = int(dps / 0.07)
    if dps_digit > 32767: dps_digit = 32767
    elif dps_digit < -32768: dps_digit = -32768
    
    return dps_digit

def set_controller_input(procon: ControllerInput, code: str, event_value: any):
    onoff_value: int = int(event_value > 0)

    if   code == 'BUTTON_A': procon.Button.A = onoff_value
    elif code == 'BUTTON_B': procon.Button.B = onoff_value
    elif code == 'BUTTON_X': procon.Button.X = onoff_value
    elif code == 'BUTTON_Y': procon.Button.Y = onoff_value
    elif code == 'BUTTON_R': procon.Button.R = onoff_value
    elif code == 'BUTTON_ZR': procon.Button.ZR = onoff_value
    elif code == 'BUTTON_L': procon.Button.L = onoff_value
    elif code == 'BUTTON_ZL': procon.Button.ZL = onoff_value
    elif code == 'BUTTON_HOME': procon.Button.Home = onoff_value
    elif code == 'BUTTON_PLUS': procon.Button.Plus = onoff_value
    elif code == 'BUTTON_MINUS': procon.Button.Minus = onoff_value
    elif code == 'BUTTON_CAPTUER': procon.Button.Capture = onoff_value
    elif code == 'DPAD_UP': procon.Dpad.Up = onoff_value
    elif code == 'DPAD_DOWN': procon.Dpad.Down = onoff_value
    elif code == 'DPAD_LEFT': procon.Dpad.Left = onoff_value
    elif code == 'DPAD_RIGHT': procon.Dpad.Right = onoff_value
    elif code == 'LSTICK_UP': procon.Stick.Left.Y = event_value
    elif code == 'LSTICK_DOWN': procon.Stick.Left.Y = event_value
    elif code == 'LSTICK_LEFT': procon.Stick.Left.X = event_value
    elif code == 'LSTICK_RIGHT': procon.Stick.Left.X = event_value
    elif code == 'LSTICK_PRESS': procon.Stick.Left.Press = onoff_value
    elif code == 'RSTICK_UP': procon.Stick.Right.Y = event_value
    elif code == 'RSTICK_DOWN': procon.Stick.Right.Y = event_value
    elif code == 'RSTICK_LEFT': procon.Stick.Right.X = event_value
    elif code == 'RSTICK_RIGHT': procon.Stick.Right.X = event_value
    elif code == 'RSTICK_PRESS': procon.Stick.Right.Press = onoff_value