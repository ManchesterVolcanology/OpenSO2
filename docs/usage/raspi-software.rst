Station Software
================
This section will outline the function of the station software in order to allow users to adapt it to their needs and for different hardware.

run_scanner.py
--------------
This is the main program that controls the scanner. The figure below outlines the workflow of the main station program ``run_scanner.py``.

.. figure:: ../Figures/scanner_flowchart.png
   :scale: 50%
   :alt: Scanner Flowchart
   :align: center
   
   Flowchart of the main station program
   
The ``run_scanner.py`` script should be launched when the Raspberry Pi boots and will perform a number of tasks before scanning begins. It is advised to have the Raspberry Pi be powered on for 1 - 2 hours either side of the scanning window to allow plenty of time for these tasks. The exact time that the station will turn on will depend on the power settings in the ``/home/pi/wittyPi/schedule.wpi`` file as described in :ref:`stationsetup`.

Modules
-------
The main program calls additional functions in order to communicate with the various components of the scanner as a whole. These can be found in the ``openso2`` library within the main ``open_so2`` directory.

**scanner**
^^^^^^^^^^^

.. automodule:: openso2.scanner
    :members:
    
**analyse_scan**
^^^^^^^^^^^^^^^^

.. automodule:: openso2.analyse_scan
    :members: analyse_scan, update_int_time

**call_gps**
^^^^^^^^^^^^

.. automodule:: openso2.call_gps
    :members: sync_gps_time

**program_setup**
^^^^^^^^^^^^^^^^^

.. automodule:: openso2.program_setup
    :members: read_settings
    
**julian_time**
^^^^^^^^^^^^^^^

.. automodule:: openso2.julian_time
    :members: hms_to_julian
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
