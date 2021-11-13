# rbpi_dht22
This script polls a number of connected DHT22 sensors, logs the data and
sends a warning by email if the values exceed the set limits.

The script will try to re-read each sensor 15 times with a 2 second wait
time in between in case it can't connect. Meaning that it can take a
maximum of just over 30 seconds to read each connected sensor.

This script is intended to be used as a cron job on a Raspberry Pi.
