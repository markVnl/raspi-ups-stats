# raspi-ups-stats

Script to show system and UPS statistics on a Raspberry Pi with [UPS Plus](https://wiki.52pi.com/index.php/UPS_Plus_SKU:_EP-0136?spm=a2g0o.detail.1000023.17.4bfb6b35vkFvoW) board and [128x64 OLED display](https://www.amazon.com/dp/B08LYL7QFQ?psc=1&ref=ppx_pop_dt_b_product_details).

## Installation

### Prerequisites

If you're using Raspbian/Raspberry Pi OS, you'll need to enable I2C using `raspi-config`.  

This script assumes the display is connected to i2c_bus 3; GPIO-5 (pin 29) is sda and GPIO-6 (pin 31)   
To enable i2c_bus 3 edit `/boot/config.txt` and add in the section of optional hardware interfaces
```
dtoverlay=i2c-gpio,i2c_gpio_sda=5,i2c_gpio_scl=6,bus=3
```
This change will take effect after the next reboot.

You'll then need to install several dependencies with 
```
sudo apt install i2c-tools python3-pip  python3-setuptools python3-pil python3-rpi.gpio libraspberrypi-bin
```

Next, you'll need libraries Adafruit's Python library for the OLED display, pi-ina219 for the power-monitors and psutils for system information. 
```
sudo pip3 install Adafruit-SSD1306
sudo pip3 install pi-ina219
sudo pip3 install psutils
```

Finally, you'll need to download the font files from https://www.dafont.com/pixel-operator.font.  The font file `PixelOperator.ttf` will need to be placed in the same directory as the executable script.

### Download and install

Change to a convenient directory and  clone or download this repository

## Auto start on boot
Create `/opt/stats/`, and copy `PixelOperator.ttf` and `stats.py` there.

Then put the systemd unit file in the correct place: `sudo cp stats.service /etc/systemd/system/`.

Then tell systemd to re-scan the unit files with `sudo systemctl daemon-reload`, and start this unit using `sudo systemctl enable --now stats`.

## Acknowledgements

Original source: https://www.the-diy-life.com/mini-raspberry-pi-server-with-built-in-ups/
Based on: https://github.com/adafruit/Adafruit_Python_SSD1306/blob/master/examples/stats.py
