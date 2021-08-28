#!/usr/bin/python3

# Copyright (c) 2017 Adafruit Industries
# Author: Tony DiCola & James DeVito
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import psutil
from collections import namedtuple
import time

import Adafruit_GPIO.I2C as I2C
from ina219 import INA219, DeviceRangeError
import Adafruit_SSD1306

from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont


def get_sysinfo(nic="eth0"):
    """
    Collect system information and return this in a named tuple
    This takes one argument : the primary NIC, defaults to eth0
    """
    SystemInfo = namedtuple("SystemInfo",
                            "IP Load LoadPercent DiskPercent DiskTotal DiskUsed MemTotal MemUsed CPUTemp")
    try:
        IP = psutil.net_if_addrs()[nic][0].address
    except KeyError:
        IP = (f"{nic} NA")
    Load = psutil.getloadavg()
    cores = psutil.cpu_count()
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    CPUTemp = psutil.sensors_temperatures()['cpu_thermal'][0].current

    IP = str(IP)
    LoadPercent = int(round((Load[1]*100)/cores))
    Load = int(Load[1])
    MemTotal = round(mem.available/(1024 ** 2))
    MemUsed = round(mem.used/(1024 ** 2))
    DiskTotal = round(disk.total/(1024 ** 3))
    DiskUsed = round(disk.used/(1024 ** 3))
    DiskPercent = int(disk.percent)
    CPUTemp = round(CPUTemp, 1)

    return SystemInfo(IP, Load, LoadPercent, DiskPercent, DiskTotal, DiskUsed, MemTotal, MemUsed, CPUTemp)


def get_upsinfo():
    """
    Collect USP information and return this in a named tuple
    """
    global ups_i2c
    global ina_i2c
    global ina_batt_i2c

    UpsInfo = namedtuple("UpsInfo",
                         "McuVccVolt PogoPinVolt BatPinCVolt UsbCVolt UsbMicroVolt "
                         "BatTemperature BatFullVolt BatEmptyVolt BatProtectVolt "
                         "BatRemaining SampleTime AutoPowerOn "
                         "PiVolt PiCurrent PiPower BattVolt BattCurrent BattPower")

    buf = []

    # UPS Register Addresses from
    # https://wiki.52pi.com/index.php/UPS_Plus_SKU:_EP-0136?spm=a2g0o.detail.1000023.17.4bfb6b35vkFvoW#USB_Plus_V5.0_Register_Mapping_Chart

    buf = ups_i2c.readList(0x00, 0x20)
    McuVccVolt = int.from_bytes([buf[0x01], buf[0x02]], byteorder='little')
    PogoPinVolt = int.from_bytes([buf[0x03], buf[0x04]], byteorder='little')
    BatPinCVolt = int.from_bytes([buf[0x05], buf[0x06]], byteorder='little')
    UsbCVolt = int.from_bytes([buf[0x07], buf[0x08]], byteorder='little')
    UsbMicroVolt = int.from_bytes([buf[0x09], buf[0x0A]], byteorder='little')
    BatTemperature = int.from_bytes([buf[0x0B], buf[0x0C]], byteorder='little')
    BatFullVolt = int.from_bytes([buf[0x0D], buf[0x0E]], byteorder='little')
    BatEmptyVolt = int.from_bytes([buf[0x0F], buf[0x10]], byteorder='little')
    BatProtectVolt = int.from_bytes([buf[0x11], buf[0x12]], byteorder='little')
    BatRemaining = int.from_bytes([buf[0x13], buf[0x14]], byteorder='little')
    SampleTime = int.from_bytes([buf[0x15], buf[0x16]], byteorder='little')
    AutoPowerOn = buf[0x19]

    # Read both ina219 powermonitors
    PiVolt = int(ina_i2c.voltage() * 1000)
    try:
        PiCurrent = int(ina_i2c.current())
        PiPower = int(ina_i2c.power())
    # FIXME : What is DeviceRangeError ?
    except DeviceRangeError:
        PiCurrent = 0
        PiPower = 0

    BattVolt = int(ina_batt_i2c.voltage() * 1000)
    try:
        BattCurrent = int(ina_batt_i2c.current())
        BattPower = int(ina_batt_i2c.power())
    # FIXME : What is DeviceRangeError ?
    except DeviceRangeError:
        BattCurrent = 0
        BattPower = 0

    return UpsInfo(McuVccVolt, PogoPinVolt, BatPinCVolt, UsbCVolt, UsbMicroVolt,
                   BatTemperature, BatFullVolt, BatEmptyVolt, BatProtectVolt,
                   BatRemaining, SampleTime, AutoPowerOn,
                   PiVolt, PiCurrent, PiPower, BattVolt, BattCurrent, BattPower)


# Setup UPS
DEVICE_BUS = 1
DEVICE_ADDR = 0x17
PROTECT_VOLT = 3700
SAMPLE_TIME = 2
INA_DEVICE_ADDR = 0x40
INA_BATT_ADDR = 0x45

ups_i2c = I2C.get_i2c_device(DEVICE_ADDR)

ina_i2c = INA219(0.00725, address=INA_DEVICE_ADDR)
ina_i2c.configure()
ina_batt_i2c = INA219(0.005, address=INA_BATT_ADDR)
ina_batt_i2c.configure()

# 128x64 display with hardware I2C:

# Note: for i2c_bus 3 add to /boot/config.txt:
# dtoverlay=i2c-gpio,i2c_gpio_sda=5,i2c_gpio_scl=6,bus=3
# then pin GPIO-5 (pin 29) is sda and GPIO-6 (pin 31) is scl of i2c_bus 3

DEVICE_BUS_DISPLAY = 3   # 1 or 3
disp = Adafruit_SSD1306.SSD1306_128_64(rst=None, i2c_bus=DEVICE_BUS_DISPLAY)

# Initialize library.
disp.begin()

# Clear display.
disp.clear()
disp.display()

# Create blank image for drawing.
# Make sure to create image with mode '1' for 1-bit color.
width = disp.width
height = disp.height
image = Image.new('1', (width, height))

# Get drawing object to draw on image.
draw = ImageDraw.Draw(image)

# Display counter
dispC = 0

# Load default font.
# font = ImageFont.load_default()

# Alternatively load a TTF font.  Make sure the .ttf font file is in the same directory as the python script!
# Some other nice fonts to try: http://www.dafont.com/bitmap.php
font = ImageFont.truetype('PixelOperator.ttf', 16)

while True:

    # Draw a black filled box to clear the image.
    draw.rectangle((0, 0, width, height), outline=0, fill=0)

    if (dispC <= 3):
        # Pi Stats Display
        sysinfo = (get_sysinfo())

        draw.text((0, 0),
                  (f"IP : {sysinfo.IP}"), font=font, fill=255)
        draw.text((0, 16),
                  (f"CPU : {sysinfo.LoadPercent} % / {sysinfo.CPUTemp} C"), font=font, fill=255)
        draw.text((0, 32),
                  (f"Mem : {sysinfo.MemUsed} / {sysinfo.MemTotal} MB"), font=font, fill=255)
        draw.text((0, 48),
                  (f"Disk : {sysinfo.DiskUsed} / {sysinfo.DiskTotal} GB"), font=font, fill=255)

    else:  # 3 < dipC = < 6
        # UPS Stats Display
        upsinfo = get_upsinfo()

        if (upsinfo.UsbCVolt > 4000):
            ChargeStat = 'Charging USB C'
        elif (upsinfo.UsbMicroVolt > 4000):
            ChargeStat = 'Charging Micro USB.'
        else:
            ChargeStat = '  ** Not Charging **'

        draw.text((0, 0),
                  (f"Pi: {upsinfo.PiVolt} mV {upsinfo.PiCurrent} mA"), font=font, fill=255)
        draw.text((0, 16),
                  (f"Batt: {upsinfo.BattVolt} mV  {upsinfo.BatRemaining} %"), font=font, fill=255)
        if (upsinfo.BattCurrent > 0):
            draw.text((0, 32),
                      (f"Chrg: {upsinfo.BattCurrent} mA {upsinfo.BattPower} W"), font=font, fill=255)
        else:
            draw.text((0, 32),
                      (f"Dchrg: {-upsinfo.BattCurrent} mA {upsinfo.BattPower} W"), font=font, fill=255)
        draw.text((0, 48), ChargeStat, font=font, fill=255)

    # Display image.
    disp.image(image)
    disp.display()

    if (dispC == 6):
        dispC = 0
    dispC += 1

    time.sleep(1)
