#!/bin/sh

while true;
do
    echo "Running STOMP publish script"
	/opt/cc/publish.py -c /opt/cc/config.ini
	sleep 5
done
