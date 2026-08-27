#!/bin/bash

# Get the WittyPi utility functions
. /home/uom/wittypi/utilities.sh

temp=$(get_temperature)
vin=$(get_input_voltage)
vout=$(get_output_voltage)
iout=$(get_output_current)

echo "$temp | $vin | $vout | $iout"
