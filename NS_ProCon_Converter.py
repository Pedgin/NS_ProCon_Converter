#!/usr/bin/env python3

import asyncio
import errno
import os
import signal
import time
from concurrent.futures import ThreadPoolExecutor
from configparser import ConfigParser
from typing import Dict, List

import evdev
import evdev.ecodes as ev
from evdev import InputDevice

import nscon
from nscon import set_controller_input

if not os.path.exists('/sys/kernel/config/usb_gadget/procon'):
    print('ProCon Gadget does not exists. Please run add_procon_gadget.sh')
    os._exit(1)

# Reset USB Gadget
os.system('echo > /sys/kernel/config/usb_gadget/procon/UDC')
os.system('ls /sys/class/udc > /sys/kernel/config/usb_gadget/procon/UDC')

time.sleep(0.5)

gadget_path: str = '/dev/hidg0'
if os.path.exists(gadget_path):
    ProCon = nscon.Controller(gadget_path)
else:
    print('Gadget Path does not exists.')
    raise FileNotFoundError(
        errno.ENOENT, os.strerror(errno.ENOENT), gadget_path)

# ////////////////////////////////USERCONFIG////////////////////////////////////

config_ini: ConfigParser = ConfigParser()
config_ini_path: str = "config.ini"

if os.path.exists(config_ini_path):
    config_ini.read(config_ini_path, encoding='utf-8')
    keyconfig: ConfigParser = config_ini['KEYCONFIG']
    devconfig: ConfigParser = config_ini['DEVICE']
else:
    print('Config File does not exists. Please check config.ini file path.')
    raise FileNotFoundError(errno.ENOENT, os.strerror(
        errno.ENOENT), config_ini_path)

devices: List[InputDevice] = [InputDevice(
    path) for path in evdev.list_devices()]

mouse = None
keybd = None

for dev in devices:
    devcapa = dev.capabilities()
    ecREL = ev.ecodes['EV_REL']
    ecKEY = ev.ecodes['EV_KEY']
    ecBTNMOUSE = ev.ecodes['BTN_MOUSE']
    if (ecREL in devcapa) and (ecBTNMOUSE in devcapa[ecKEY]):
        mouse = dev
    elif (ecREL not in devcapa) and (ecKEY in devcapa):
        keybd = dev

if not mouse or not keybd:
    print('Input Device dose not exists. Please check valid device list.')
    print('Valid Device List')
    for device in devices:
        print(f'\t{device.path} {device.name} {device.phys}')
    os._exit(1)

evkeys: Dict[int, str] = {ev.ecodes[key.upper()]: key.upper()
                          for key in keyconfig}
turn_dots: float = float(devconfig['MouseDPI']) * \
    (float(devconfig['MouseTurnDistance']) / 2.54)
dot_per_digit: float = (turn_dots / 180) * 0.07
ProCon.Input.Sensor.Gyro.Sensitivity = dot_per_digit
ProCon.applySens = ['gyroy', 'gyroz']
ProCon.LogLevel = 2

# //////////////////////////////////////////////////////////////////////////////

# TODO: REL_WHEEL
async def mouse_events(mouse: InputDevice):
    async for event in mouse.async_read_loop():
        if event.type == ev.ecodes['EV_REL'] and event.code in [ev.ecodes['REL_X'], ev.ecodes['REL_Y']]:
            if event.code == ev.ecodes['REL_X']:
                ProCon.Input.Sensor.Gyro.Z += event.value
            elif event.code == ev.ecodes['REL_Y']:
                ProCon.Input.Sensor.Gyro.Y += event.value
        elif event.type == ev.ecodes['EV_KEY'] and event.code in evkeys:
            set_controller_input(
                ProCon.Input, keyconfig[evkeys[event.code]], event.value)


async def keybd_events(keybd: InputDevice):
    async for event in keybd.async_read_loop():
        if event.type == ev.ecodes['EV_KEY'] and event.code in evkeys:
            ConInput = keyconfig[evkeys[event.code]]
            if ConInput.endswith(('STICK_UP', 'STICK_RIGHT')):
                set_value = 0xFFF if event.value else 0x800
            elif ConInput.endswith(('STICK_DOWN', 'STICK_LEFT')):
                set_value = 0x000 if event.value else 0x800
            else:
                set_value = event.value
            set_controller_input(ProCon.Input, ConInput, set_value)


def hand(signal, frame):
    ProCon.Disconnect()
    ProCon.Close()
    os.system('echo > /sys/kernel/config/usb_gadget/procon/UDC')
    os.system('ls /sys/class/udc > /sys/kernel/config/usb_gadget/procon/UDC')
    time.sleep(0.5)
    os._exit(1)


ProCon.startConnect()

asyncio.ensure_future(mouse_events(mouse))
asyncio.ensure_future(keybd_events(keybd))

loop = asyncio.get_event_loop()
executor: ThreadPoolExecutor = ThreadPoolExecutor()
executor.submit(loop.run_forever)

signal.signal(signal.SIGINT, hand)
