# Open SO<sub>2</sub>
Open Source SO<sub>2</sub> flux software for volcano monitoring

## Raspberry Pi Setup Instructions
The Open SO<sub>2</sub> scanner uses open source software written in Python to control commercially available components based on the Raspberry Pi to control UV scanning spectrometers for measuring volcanic SO<sub>2</sub> fluxes.

This guide will outline the steps to installing the necessary software onto the Raspberry Pi.

### Python - Anaconda
Python is already installed on the Raspberry Pi, but Anaconda is recommended for the spectrometer control. For the Raspberry Pi a version called Berryconda is used, which can be downloaded [here](https://github.com/jjhelmus/berryconda). Python 3 should be used. Be sure to add anaconda to PATH.

### Python Seabreeze
The Ocean Optics spectrometer is controlled using a Python library called Python Seabreeze, which is maintained on GitHub [here](https://github.com/ap--/python-seabreeze). The library is installed using:
```
conda install –c poehlmann python-seabreeze 
```
The udev rules must then be downloaded from [here](https://github.com/ap--/python-seabreeze/blob/master/misc/10-oceanoptics.rules) and saved into the ```/etc/udev/rules.d/``` directory and updated using:
```
sudo udevadm control –reload-rules
```

### WittyPi 2 HAT
The power to the Pi is controlled using the WittyPi2 HAT. This controls when the Pi powers down and up to save electricity while it is dark. Details can be found [here](http://www.uugear.com/doc/WittyPi2_UserManual.pdf). To install the required software use the following commands from the home directory:
```
wget http://www.uugear.com/repo/WittyPi2/installWittyPi.sh
sudo sh installWittyPi.sh
```
This script goes through several steps to ensure the WittyPi2 board will operate correctly. Note it is not necessary to install Qt for the GUI. Once it is installed a correct script to tell the board when to power on and off is required. In the wittyPi folder create a text document called ```schedule.wpi``` containing the following text:
```
BEGIN 2018-01-01 06:00:00
END   2050-01-01 23:59:59
ON    12H
OFF   12H
```
This script tells the wittyPi board to turn the Pi on from 6:00 to 18:00 everyday. Not that this is UTC, so the ```BEGIN``` time will require adjusting for the local time zone. The script is then activated by running
```
sudo ./run_script.sh
```
This will summerise the timing details so they can be checked.

### Adafruit Motor HAT
Control of the stepper motor in the scanner is achieved using this HAT. Details can be found [here](https://learn.adafruit.com/circuitpython-on-raspberrypi-linux/installing-circuitpython-on-raspberry-pi). To operate first you need to install Adafruit Blinka following these steps:
```
pip install –upgrade setuptools
```
Next enable I2C and SPI and reboot. Then run the following commands:
```
pip install RPI.GPIO
pip install adafruit-blinka
```
Then install the circuit python library for motor control
```
pip install adafruit-circuitpython-motorkit
```

### GPS
To obtain the GPS information requires the GPS module in python as well as GSPD to talk to the GPS device. To install these run:
```
sudo apt-get install gpsd gpsd-clients
pip install gps
```
Open SO<sub>2</sub> also changes the RTC time of the wittyPi board to make sure that the board time matches the system time of the Pi when connected to the GPS. This requires the ```system_to_rtc.sh``` file to be placed in the wittyPi folder. Make sure it is executeable with ```chmod +x system_to_rtc.sh```

You should also check that the time zone for the Pi is set to UTC. Run:
```
sudo dpkg-reconfigure tzdata
```
Then select ```None of the above``` and set the TZ to UTC.

### Start up script
Open SO<sub>2</sub> is designed to run on startup. This is achieved by following these steps.

First make sure the script ```run_scanner.py``` is executable by navigating to the open_so2 folder and running:
```
chmod +x run_scanner.py
```
Now to make sure it runs on startup add the following lines to the startup script found at ```/etc/rc.local``` above the ```exit 0``` line:
```
sudo systemctl stop gpsd.socket
sudo systemctl disable gpsd.socket
sudo gpsd /dev/ttyUSB0 -F /var/run/gpsd.sock

cd /home/pi/open_so2/
sudo /home/pi/open_so2/./run_scanner.py
```
