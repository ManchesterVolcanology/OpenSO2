Station Setup
=============

The station has several core components:

* The control computer
* The spectrometer (and associated optics)
* Power control
* The motor
* GPS (for time keeping)
* Communication

This section will describe the setup and operation of each of these components in the Open |SO2| scanner.

.. note:: The station software is designed to be modular so that the specific components used can be changed with relative ease. 

The Control Computer
^^^^^^^^^^^^^^^^^^^^

The Open |SO2| software has been designed to work on a Raspberry Pi single board computer (specifically the RPI 3B+). The only addition to

Spectrometer
^^^^^^^^^^^^
The Open |SO2| station is designed to work with an Ocean Optics USB spectrometer. The spectrometer is controlled through a Python library called Python Seabreeze, which is maintained on GitHub `here <https://github.com/ap--/python-seabreeze>`_ .

The spectrometer is connected to the Raspberry Pi by a USB cable which provides power and control.

Stepper Motor
^^^^^^^^^^^^^
The scanner head is rotated using a stepper motor controlled by the Raspberry Pi. The motor requires a separate control board to operate with a separate power supply. 

The Open |SO2| scanner uses a board called the `Adafruit Motor HAT. <https://www.adafruit.com/product/2348>`_ to control the stepper motor. Details can be found in the Adafruit documentation. To operate the HAT Adafruit Blinka must first be installed::
	
	pip install -upgrade setuptools
	
Next enable I2C and SPI and reboot. Then run the following commands::

	pip install RPI.GPIO
	pip install adafruit-blinka
	
Then install the circuit python library for motor control::

	pip install adafruit-circuitpython-motorkit
	
The motor control should now work.

GPS
^^^
To obtain the GPS information requires the GPS module in python as well as GSPD to talk to the GPS device. To install these run::

	sudo apt-get install gpsd gpsd-clients
	pip install gps
	
Open |SO2| also changes the RTC time of the wittyPi board to make sure that the board time matches the system time of the Pi when connected to the GPS. This requires the ``system_to_rtc.sh`` file to be placed in the wittyPi folder. Make sure it is executeable with ``chmod +x system_to_rtc.sh``

You should also check that the time zone for the Pi is set to UTC by running::

	sudo dpkg-reconfigure tzdata
	
selecting ``None of the above`` and setting the TimeZone to UTC.

.. Substitutions
.. |SO2| replace:: SO\ :sub:`2`
