Home Station Setup
==================
.. _home-setup-ref:

The Open |SO2| scanners are designed to work as a network, with a central home station computing SO2 fluxes in real time, given the geometry of the volcano and scanners as well as real time wind data.

Installation
------------

The home software is currently run as a python script (written in python 3.6). The easiest way to get python up and running is using `Anaconda <https://www.anaconda.com/>`_ which comes with most of the required libraries. The only extra library required is ``pysftp`` which handles transferring files via SFTP from the Pi to the home computer. This can be installed using pip::

    pip install pysftp

or with conda::

    conda install -c conda-forge pysftp

Now the home software can be launched from the command line by navigating to the ``open_so2/`` folder and running::

    python open_so2.py
    
This will open the Open |SO2| GUI interface and begin the program.

.. note:: An executable version is planned for the future.

Station Connection Setup
------------------------

To allow the home software to talk to the stations via SSH it requires the IP address, user name and password for the station. The username and password can be configured on the Pi manually, and the IP address is determined by the network. This information is stored in the ``station_info.txt`` input file in the ``data_bases/`` directory. It has the following format::

      Station Name   ;      Host      ;   Username   ;  Password   
    [Station 1 Name] ; [IP Address 1] ; [Username 1] ; [Password 1]
    [Station 2 Name] ; [IP Address 2] ; [Username 2] ; [Password 2]
    .
    .
    .

where each station has an entry on a seperate line. Note that the header line and any whitespace is ignored. 

.. Substitutions
.. |SO2| replace:: SO\ :sub:`2`
