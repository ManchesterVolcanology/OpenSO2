# Open SO<sub>2</sub>
Open Source SO<sub>2</sub> flux software for volcano monitoring. See the full documentation [here](https://open-so2.readthedocs.io/en/latest/index.html).

## Raspberry Pi Setup Instructions
The Open SO<sub>2</sub> scanner uses open source software written in Python to control easily available components based on the Raspberry Pi to control UV scanning spectrometers for measuring volcanic SO<sub>2</sub> fluxes.

This guide will outline the steps to installing the necessary software onto the Raspberry Pi.

### Raspian
Before starting you will need an SD card with the Raspberry Pi operating sustem (Raspian) installed. You should not use a pre-loaded SD card with NOOBS installed as this casues issues with the WittyPi board (see below). Instead, write the OS directly onto the SD card. There are extensive instructions on how to do this on the Raspberry Pi website. 

### Python
OpenSO<sub>2</sub> is written in Python3. Usually Raspbian will come with both a Python2 and Python3, so make sure you use Python3 (and pip3 when installing libraries) as the default is likely Python2.

### Python libraries
There are several libraries required for OpenSO<sub>2</sub> beyond the base libraries:
- Numpy
- Scipy
- Pandas
- PyYaml
- GPIOzero

These can be installed using pip3:

```
pip3 install numpy scipy pandas PyYAML GPIOzero
```

There are a number of additional specialised libraries that are also required, these are detailled below.

### Python Seabreeze
The Ocean Optics spectrometer is controlled using a Python library called Python Seabreeze, which is maintained on GitHub [here](https://github.com/ap--/python-seabreeze). The library is installed using:
```
pip3 install seabreeze 
```
To allow the RPi to talk to the spectrometer the udev rules must updated using:
```
seabreeze_os_setup
```
Note that you may have to close and open the terminal before running this command.

### GPS
To obtain the GPS information requires the GPS module in python as well as GSPD to talk to the GPS device. To install these run:
```
sudo apt-get install gpsd gpsd-clients
pip3 install gps
```

### WittyPi HAT
The power to the Pi is controlled using the WittyPi HAT. This controls when the Pi powers down and up to save electricity while it is dark. Details can be found [here](http://www.uugear.com/doc/WittyPi2_UserManual.pdf). To install the required software use the following commands from the home directory (NOTE! it is strongly suggested that this is done before mounting the WittyPi board):
```
wget http://www.uugear.com/repo/WittyPi2/installWittyPi.sh
sudo sh installWittyPi.sh
```
or 
```
wget http://www.uugear.com/repo/WittyPi3/install.sh
sudo sh installWittyPi.sh
```
Depending on whether you have the 2 or 3 board. This script goes through several steps to ensure the WittyPi board will operate correctly. Note it is not necessary to install Qt for the GUI. Once it is installed a correct script to tell the board when to power on and off is required. In the ```/home/pi/wittyPi``` folder create a text document called ```schedule.wpi``` containing the following text:
```
BEGIN 2018-01-01 06:00:00
END   2050-01-01 23:59:59
ON    H12
OFF   H12
```
This script tells the wittyPi board to turn the Pi on from 6:00 to 18:00 everyday. Not that this is UTC, so the ```BEGIN``` time will require adjusting for the local time zone. The script is then activated by running
```
sudo ./run_script.sh
```
This will summerise the timing details so they can be checked.

> :warning: There is an issue with using the WittyPi software when using Raspian with NOOBS. Details on how to work around this can be found in the WittyPi user manual.

Open SO<sub>2</sub> also changes the RTC time of the wittyPi board to make sure that the board time matches the system time of the Pi when connected to the GPS. This requires the ```system_to_rtc.sh``` file to be placed in the wittyPi folder. Make sure it is executeable with ```chmod +x system_to_rtc.sh```

You should also check that the time zone for the Pi is set to UTC. Run:
```
sudo dpkg-reconfigure tzdata
```
Then select ```None of the above``` and set the TZ to UTC.

### Adafruit Motor HAT
Control of the stepper motor in the scanner is achieved using this HAT. Details can be found [here](https://learn.adafruit.com/circuitpython-on-raspberrypi-linux/installing-circuitpython-on-raspberry-pi). To operate first you need to install Adafruit Blinka following these steps:
```
pip3 install –upgrade setuptools
```
Next enable I2C and SPI and reboot. Then run the following commands:
```
pip3 install RPI.GPIO
pip3 install adafruit-blinka
```
Then install the circuit python library for motor control
```
pip3 install adafruit-circuitpython-motorkit
```

### Start up script
Open SO<sub>2</sub> is designed to run on startup. This is achieved with crontab. To set this up, open the crontab editor using

```
crontab -e
```

Then at the bottom of the file add the following line:

```
@reboot cd /home/pi/open_so2/ && python3 run_scanner.py &
```

### Wiring
This image shows the wiring of the control boards for the Open SO<sub>2</sub> scanner.

![Scanner wiring](https://github.com/benjaminesse/open_so2/blob/master/docs/Figures/controller_wiring.png "Controller Wiring")

## Home Station Software Setup

### Installing
The Open SO<sub>2</sub> scanners are designed to work as a network, with a central home station computing SO<sub>2</sub> fluxes in real time, given the geometry of the volcano and scanners as well as real time wind data.

The home software is currently run as a python script (written in python 3.6). The easiest way to get python up and running is using Anaconda (https://www.anaconda.com/) which comes with most of the required libraries. The best method to install is to create a new virtual environment for the software:

```
conda create -n openso2 python=3.6 numpy scipy pandas pyyaml pyqt pyqtgraph
```

This will create the environment and install some of the libraries on the main Anaconda channel. Down activate the environment:

```
conda activate openso2
```

and install the remaining libraries from conda-forge:

```
conda install -c conda-forge pyside2 pysftp
```

Now the home software can be launched from the command line.
