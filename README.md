# Open SO<sub>2</sub>
Open Source SO<sub>2</sub> flux software for volcano monitoring

## Raspberry Pi Setup Instructions
The Open SO<sub>2</sub> scanner uses open source software written in Python to control commercially available components based on the Raspberry Pi to control UV scanning spectrometers for measuring volcanic SO<sub>2</sub> fluxes.

This guide will outline the steps to installing the necessary software onto the Raspberry Pi.

### Python - Anaconda
Python is already installed on the Raspberry Pi, but Anaconda is recommended for the spectrometer control. This can be downloaded [here](https://github.com/jjhelmus/berryconda). Python 3 should be used. Be sure to add anaconda to PATH.

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
The power to the Pi is controlled using the WittyPi2 HAT. This controls when the Pi powers down and up to save electricity while it is dark. Details can be found [here] (http://www.uugear.com/doc/WittyPi2_UserManual.pdf). To install the required software use the following commands from the home directory:
```
wget http://www.uugear.com/repo/WittyPi2/installWittyPi.sh
sudo sh installWittyPi.sh
```
This script goes through several steps to ensure the WittyPi2 board will operate correctly. Note it is note necessary to install Qt for the GUI.

### Adafruit Motor HAT
Control of the stepper motor in the scanner is achieved using this HAT. Details can be found [here] (https://learn.adafruit.com/circuitpython-on-raspberrypi-linux/installing-circuitpython-on-raspberry-pi). To operate first you need to install Adafruit Blinka following these steps:
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
