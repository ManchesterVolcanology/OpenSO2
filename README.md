# Open SO<sub>2</sub>
Open Source SO<sub>2</sub> flux software for volcano monitoring. See the full documentation [here](https://open-so2.readthedocs.io/en/latest/index.html).

## Raspberry Pi Setup Instructions
The Open SO<sub>2</sub> scanner uses open source software written in Python to control easily available components based on the Raspberry Pi to control UV scanning spectrometers for measuring volcanic SO<sub>2</sub> fluxes.

This guide will outline the steps to installing the necessary software onto the Raspberry Pi.

First install PiOS bookworm (64bit) and set time zone to UTC

# Check for updates
```
sudo apt update
sudo apt upgrade
```
# WittyPi
```
wget http://www.uugear.com/repo/WittyPi4/install.sh
sudo sh install.sh
```
`nano schedule.wpi`:
```
BEGIN 2018-01-01 06:00:00
END   2030-01-01 23:59:59
ON    H12
OFF   H12
```
To install the script run: `sudo ./runScript.sh`
# Python
```
python -m venv venv

source venv/bin/activate

sudo apt install libusb-dev

pip install numpy scipy pandas xarray pyyaml utm pyserial seabreeze adafruit-blinka adafruit-circuitpython-motorkit plotly gunicorn Dash dash_bootstrap_components gpiozero

seabreeze_os_setup
```
# OpenSO2
```
git clone https://github.com/ManchesterVolcanology/OpenSO2.git
cd OpenSO2
git switch v1.5
sudo chmod 777 write_rtc_time.sh
cp Station/station_settings_ex.yml Station/station_settings.yml
nano station_settings.yml
```
And update required settings

Also remember to add an ILS file for the spectrometer, e.g.:
`FLMxxxxx_ils.txt`:
```
0.6
2.0
0.0
0.0
```
# Wiring:
Motor:
- 1: Red
- 2: Yellow
- 3: Nothing
- 4: Brown
- 5: Orange

GPIO:
- +5V: Blue
- GND: Black
- I/O 27: White
- I/O 21: Grey
- I/O 13: Green

## Start up script
Open SO<sub>2</sub> is designed to run on startup. This is achieved with crontab. To set this up, open the crontab editor using

```
crontab -e
```

Then at the bottom of the file add the following line:

```
@reboot cd /home/scan/OpenSO2/ && /home/scan/venv/bin/python run_scanner.py &
```
