# Open SO<sub>2</sub>
Open Source SO<sub>2</sub> flux software for volcano monitoring. See the full documentation [here](https://open-so2.readthedocs.io/en/latest/index.html).

## Raspberry Pi Setup Instructions
The Open SO<sub>2</sub> scanner uses open source software written in Python to control easily available components based on the Raspberry Pi to control UV scanning spectrometers for measuring volcanic SO<sub>2</sub> fluxes.

This guide will outline the steps to installing the necessary software onto the Raspberry Pi.

### Raspian
Before starting you will need an SD card with the Raspberry Pi operating sustem (Raspian) installed. You should not use a pre-loaded SD card with NOOBS installed as this casues issues with the WittyPi board (see below). Instead, write the OS directly onto the SD card. There are extensive instructions on how to do this on the Raspberry Pi website. 

## Installing OpenSO2

There will be an image of Raspian Bullseye with everything ready to go...

But to set this up, first image an SD card with Raspian Lite (without any desktop or extra apps, to save space). Make sure to enable SSH and set up any network settings to allow access to the Pi.

Once the Raspberry Pi is ready to go, we will first run a quick update to ensure everything is up-to-date:

```
sudo apt update
sudo apt upgrade
```

Next we need to install pip (the python package manager) and Git (for getting the OpenSO2 software):

```
sudo apt install python3-pip
sudo apt install git
```

Make sure pip is up to date:

```
python -m pip install --upgrade pip
```

Before installing the required libraries, we need to update the numpy that ships with Raspian, and install libatlas3-base:

```
sudo apt remove python3-numpy
sudo apt install libatlas3-base
```

Next we will need to get the required Python libraries installed:

```
pip install numpy scipy==1.8.1 pandas xarray pyyaml utm pyserial seabreeze adafruit-blinka adafruit-circuitpython-motorkit plotly gunicorn Dash dash_bootstrap_components
```

Here, `numpy`, `scipy`, `pandas`, `xarray`, `pyyaml`, `utm`, `pyserial`, `seabreeze`, `adafruit-blinka` and `adafruit-circuitpython-motorkit` are used for the main scanner script, while `plotly`, `gunicorn`, `Dash` and `dash_bootstrap_components` are for the server for the scanner.

Note that scipy version 1.8.1 is the latest that works (at the time of writing). I am not sure what the issue is with later versions...

To allow the Pi to talk to the spectrometer the udev rules must updated using (you may have to restart the terminal):

```
seabreeze_os_setup
```

Once Python is all set up, clone this repository onto the scanner in the `/home/pi` directory.

## Install WittyPi software

The WittyPi board is used to control when the scanner wakes up and goes to sleep. You will need to get the required software for the board. From the `/home/pi` directory run the following:

```
wget http://www.uugear.com/repo/WittyPi3/install.sh
```
for the WittPi3, or

```
wget http://www.uugear.com/repo/WittyPi4/install.sh
```
for the WittyPi4. Then:
```
sudo sh install.sh
```

Once it is installed a correct script to tell the board when to power on and off is required. In the `/home/pi/wittyPi` folder create a text document called `schedule.wpi` containing the following text:

```
BEGIN 2018-01-01 06:00:00
END   2030-01-01 23:59:59
ON    H12
OFF   H12
```

The exact times will need to be updated with your local time (as the Pi will work in UTC). The `BEGIN` option is the wake up time, `ON` sets how long the Pi will be on for and `OFF` how long it will be off for. Note that `ON` and `OFF` should add up to 24 hours.

## Start up script
Open SO<sub>2</sub> is designed to run on startup. This is achieved with crontab. To set this up, open the crontab editor using

```
crontab -e
```

Then at the bottom of the file add the following line:

```
@reboot cd /home/pi/OpenSO2/ && python run_scanner.py &
```
