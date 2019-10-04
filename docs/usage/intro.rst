Open |SO2|
##########

What is Open |SO2|?
===================

Open |SO2| is open source software for controlling a scanning UV spectrometer to calculate volcanic |SO2| fluxes.

There are two main components: the home computer software and the scanner station software. The stations are controlled by a Raspberry Pi computer and complete scans of the plume, analysing the spectra in real time. These scans are then collected by the home computer via sFTP and used to calculate the flux, given a wind speed, plume height and plume direction (either calculated from two scans or set manually).

The Open |SO2| system is designed to be open source and flexible. All software is writen in Python and the components are all commertially available, requiring only basic electronics understanding to build - indeed it is our hope that the volcanic gas community will work together to improve this beyond the groundwork laid out here!

If you would like to be involved in the project please contact Ben Esse (benjamin.esse@manchester.ac.uk).

Installation
============

To install Open |SO2| simply clone the `git repositry <https://github.com/benjaminesse/open_so2>`_. This contains both the home computer and scanner station software 

.. Substitutions
.. |SO2| replace:: SO\ :sub:`2`
