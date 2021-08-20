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
import smbus2
import logging
from ina219 import INA219,DeviceRangeError

import Adafruit_GPIO.SPI as SPI
import Adafruit_SSD1306

from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont


def get_sysinfo(nic="eth0"):
    """
    Collect system information and return this as strings in a named tuple
    This takes one argument : the primary NIC, defaults to eth0
    """
    Systeminfo = namedtuple(
        "Systeminfo", "ip load loadpercent diskpercent disktotal diskused memtotal memused temp")
    try:
        ip = psutil.net_if_addrs()[nic][0].address
    except KeyError:
        ip = (f"{nic} NA")
    load = psutil.getloadavg()
    cores = psutil.cpu_count()
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    temp = psutil.sensors_temperatures(fahrenheit=False)['cpu_thermal'][0].current

    ip = str(ip)
    loadpercent = str(round((load[1]*100)/cores))
    load = str(load[1])
    memtotal = str(round(mem.available/(1024 ** 2)))
    memused = str(round(mem.used/(1024 ** 2)))
    disktotal = str(round(disk.total/(1024 ** 3)))
    diskused = str(round(disk.used/(1024 ** 3)))
    diskpercent = str(disk.percent)
    temp = str(round(temp,1))

    return Systeminfo(ip, load, loadpercent, diskpercent, disktotal, diskused, memtotal, memused, temp)

# Setup UPS
DEVICE_BUS = 1
DEVICE_ADDR = 0x17
PROTECT_VOLT = 3700
SAMPLE_TIME = 2
INA_DEVICE_ADDR = 0x40
INA_BATT_ADDR = 0x45

bus = smbus2.SMBus(DEVICE_BUS)

ina = INA219(0.00725, address=INA_DEVICE_ADDR)
ina.configure()
ina_batt = INA219(0.005, address=INA_BATT_ADDR)
ina_batt.configure()

#Set up Display
# Raspberry Pi pin configuration:
RST = None     # on the PiOLED this pin isnt used

# 128x64 display with hardware I2C:
disp = Adafruit_SSD1306.SSD1306_128_64(rst=RST)

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

# Draw a black filled box to clear the image.
draw.rectangle((0,0,width,height), outline=0, fill=0)

# Draw some shapes.
# First define some constants to allow easy resizing of shapes.
padding = -2
top = padding
bottom = height-padding
# Move left to right keeping track of the current x position for drawing shapes.
x = 0

# Display counter
dispC = 0

# Load default font.
# font = ImageFont.load_default()

# Alternatively load a TTF font.  Make sure the .ttf font file is in the same directory as the python script!
# Some other nice fonts to try: http://www.dafont.com/bitmap.php
font = ImageFont.truetype('PixelOperator.ttf', 16)

while True:

    # Draw a black filled box to clear the image.
    draw.rectangle((0,0,width,height), outline=0, fill=0)

    # Scripts for UPS monitoring

    piVolts = round(ina.voltage(),2)
    piCurrent = round (ina.current())
    
    battVolts = round(ina_batt.voltage(),2)
    
    try:
        battCur = round(ina_batt.current())
        battPow = round(ina_batt.power()/1000,1)
    except DeviceRangeError:
        battCur = 0
        battPow = 0
    

    try:
        
        aReceiveBuf = bus.read_i2c_block_data(DEVICE_ADDR, 0, 32)
    
        if (aReceiveBuf[8] << 8 | aReceiveBuf[7]) > 4000:
            chargeStat = 'Charging USB C'
        elif (aReceiveBuf[10] << 8 | aReceiveBuf[9]) > 4000:
            chargeStat = 'Charging Micro USB.'
        else:
            chargeStat = 'Not Charging'
    
        battTemp = (aReceiveBuf[12] << 8 | aReceiveBuf[11])
        battCap = (aReceiveBuf[20] << 8 | aReceiveBuf[19])
    
    except:
        chargeStat = 'Error reading UPS' 
        #FIXME probably we want to log this and not just pass... 
        pass

    if (dispC <= 15):
        # Pi Stats Display
        sysinfo = (get_sysinfo())

        draw.text(((x, top+2),
                (f"IP : {sysinfo.ip}"), font=font, fill=255)
        draw.text((x, top+18),
                (f"CPU : {sysinfo.loadpercent} %"), font=font, fill=255)
        draw.text((x+80, top+18),
                (f"{sysinfo.temp} C"), font=font, fill=255)
        draw.text((x, top+34),
                (f"Mem : {sysinfo.memused} / {sysinfo.memtotal} MB"), font=font, fill=255)
        draw.text((x, top+50),
                (f"Disk : {sysinfo.diskused} /  {sysinfo.disktotal} GB"), font=font, fill=255)
        dispC+=1
        
    else:
    
        # UPS Stats Display
        draw.text((x, top+2), "Pi: " + str(piVolts) + "V  " + str(piCurrent) + "mA", font=font, fill=255)
        draw.text((x, top+18), "Batt: " + str(battVolts) + "V  " + str(battCap) + "%", font=font, fill=255)
        if (battCur > 0):
            draw.text((x, top+34), "Chrg: " + str(battCur) + "mA " + str(battPow) + "W", font=font, fill=255)
        else:
            draw.text((x, top+34), "Dchrg: " + str(0-battCur) + "mA " + str(battPow) + "W", font=font, fill=255)
        draw.text((x+15, top+50), chargeStat, font=font, fill=255)
        dispC+=1
        if (dispC == 30):
            dispC = 0

    # Display image.
    disp.image(image)
    disp.display()
    time.sleep(.1)
