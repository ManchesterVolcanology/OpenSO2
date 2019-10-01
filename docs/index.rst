.. Open SO2 documentation master file

Open |SO2| documentation
###############################

About Open |SO2|
=======================
Open |SO2| is open source software for controlling a scanning UV spectrometer to calculate volcanic |SO2| fluxes.

There are two main components: the home computer software and the scanner station software. The stations are controlled by a Raspberry Pi computer and complete scans of the plume, analysing the spectra in real time. These scans are then collected by the home computer via sFTP and used to calculate the flux, given a wind speed, plume height and plume direction (either calculated from two scans or set manually).

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   usage/installation
   usage/raspi-setup


Guide
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`


.. |SO2| replace:: SO\ :sub:`2`
