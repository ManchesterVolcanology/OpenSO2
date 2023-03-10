#!/bin/bash

# Get the WittyPi utility functions
. /home/pi/wittypi/utilities.sh

# Run a loop to update the board status file every 5 seconds
while true; do

    sleep 5 &

    temp=$(get_temperature)
    vin=$(get_input_voltage)
    vout=$(get_output_voltage)
    iout=$(get_output_current)

    echo "temperature: $temp" > /home/pi/OpenSO2/Station/board_status.yml
    echo "Vin: $(printf %.02f $vin)" >> /home/pi/OpenSO2/Station/board_status.yml
    echo "Vout: $(printf %.02f $vout)" >> /home/pi/OpenSO2/Station/board_status.yml
    echo "Iout: $(printf %.02f $iout)" >> /home/pi/OpenSO2/Station/board_status.yml

    wait
done
