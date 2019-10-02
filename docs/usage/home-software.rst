Home Software
=============

The home computer software is controlled through a GUI that allows the user to see the status of the different stations, set the flux calculation settings and view the latest scans.

The following section will outline the function and operation of each part of the program.

Sync Settings
-------------

Results Folder
^^^^^^^^^^^^^^
This defines the location that the synced files and results will be saved to. The default is a folder called ``Results/`` in the same directory as the main program.

Sync Delay
^^^^^^^^^^
This defines the frequency with which the program will sync with the scanning staitons. Default is 30 seconds.

Status Indicator
^^^^^^^^^^^^^^^^
Gives an indication of whether the program is in Standby or actively Syncing. This indicator will also cycle between green and red.

Flux Settings
-------------

Plume Height
^^^^^^^^^^^^
The height of the plume in meters above sea level. Can either be set to be fixed at a user defined height or calculated from the scanners. 

Wind Speed
^^^^^^^^^^
Controls the wind speed the program uses. It is either a fixed value or read from a real time wind file.

Wind Bearing
^^^^^^^^^^^^
Controls the direction of the wind. It is either a fixed value or pulled from a real time wind file.

Graph Display
-------------
The graph area shows three plots:

1. A time series of the flux calculated form each station
2. The last scan to be synced
3. A time series of the wind speed

Text Output
-----------
A text box to display status updates from the program.



