#!/bin/sh
#Set current directory
cd "$(dirname "$0")"

while true;
do
    echo "Running STOMP to MongoDB bridge"
	./subscribe.py -c config.ini $@
	sleep 5
done
