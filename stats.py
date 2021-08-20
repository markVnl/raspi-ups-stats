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
from ina219 import INA219,DeviceRangeError
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

ups_i2c = I2C.get_i2c_device(DEVICE_ADDR)

ina_i2c = INA219(0.00725, address=INA_DEVICE_ADDR)
ina_i2c.configure()
ina_batt_i2c = INA219(0.005, address=INA_BATT_ADDR)
ina_batt_i2c.configure()

# 128x64 display with hardware I2C:

# Note: for i2c_bus 3 add to /boot/config.txt:
# dtoverlay=i2c-gpio,i2c_gpio_sda=5,i2c_gpio_scl=6,bus=3
# then pin GPIO-5 (pin 29) is sda and GPIO-6 (pin 31) is scl of i2c_bus 3

DEVICE_BUS_DISPLAY = 1   # 1 or 3
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
    draw.rectangle((0,0,width,height), outline=0, fill=0)

    if (dispC <= 3):
        # Pi Stats Display
        sysinfo = (get_sysinfo())

        draw.text((0, 0),
                (f"IP : {sysinfo.ip}"), font=font, fill=255)
        draw.text((0, 16),
                (f"CPU : {sysinfo.loadpercent} %"), font=font, fill=255)
        draw.text((80, 16),
                (f"{sysinfo.temp} C"), font=font, fill=255)
        draw.text((0, 32),
                (f"Mem : {sysinfo.memused} / {sysinfo.memtotal} MB"), font=font, fill=255)
        draw.text((0, 48),
                (f"Disk : {sysinfo.diskused} /  {sysinfo.disktotal} GB"), font=font, fill=255)
                
    else: # 3 < dipC = < 6
        
        # Scripts for UPS monitoring

        piVolts = round(ina_i2c.voltage(),2)
        piCurrent = round(ina_i2c.current())
        
        battVolts = round(ina_batt_i2c.voltage(),2)
        
        try:
            battCur = round(ina_batt_i2c.current())
            battPow = round(ina_batt_i2c.power()/1000,1)
        except DeviceRangeError:
            battCur = 0
            battPow = 0
        

        try:
            
            aReceiveBuf = ups_i2c.readList(0, 32)
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

        # UPS Stats Display
        draw.text((0, 0), "Pi: " + str(piVolts) + "V  " + str(piCurrent) + "mA", font=font, fill=255)
        draw.text((0, 16), "Batt: " + str(battVolts) + "V  " + str(battCap) + "%", font=font, fill=255)
        if (battCur > 0):
            draw.text((0, 32), "Chrg: " + str(battCur) + "mA " + str(battPow) + "W", font=font, fill=255)
        else:
            draw.text((0, 32), "Dchrg: " + str(0-battCur) + "mA " + str(battPow) + "W", font=font, fill=255)
        draw.text((15, 48), chargeStat, font=font, fill=255)

    # Display image.
    disp.image(image)
    disp.display()
     
    if (dispC == 6):
        dispC = 0
    dispC+=1 

    time.sleep(1)
