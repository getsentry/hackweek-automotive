#!/bin/bash

OBD_MAC=$(cat /opt/carbuddy/config/obd_mac_address.txt | tr -d '[:space:]')

if [ -z "$OBD_MAC" ]; then
    echo "ERROR: No MAC address found" >&2
    exit 1
fi

rfcomm connect hci0 "$OBD_MAC"
