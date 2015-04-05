#!/usr/bin/python
# Stomp reader for TEDDI sensors
# 
# Original code by Sebastian Mellor @ Culture Lab Newcastle
#     s.j.i.mellor@newcastle.ac.uk
# Based on Stomp.py example code at
#     http://code.google.com/p/stomppy/wiki/SimpleExample
# 
# Regex compilation and argparse added by
#     Sam Mitchell Finnigan
#

import argparse
import ConfigParser
import io
from datetime import datetime
import logging
import os, errno
import re
import serial
from stompy.simple import Client
import sys
import time

from subprocess import Popen

#logging.basicConfig(level=logging.DEBUG)

## Argument parsing from command line
parser = argparse.ArgumentParser(description='Read data from the CurrentCost EnviR located at the serial device specified')

parser.add_argument('-v','--verbose', action="count",  dest='verbosity', help='verbose output', default=0)
parser.add_argument('-c','--config',  action="store",  dest='config',    type=str,  help='Configuration File', default='config.ini')

args = parser.parse_args()

## Read configuration file
config = ConfigParser.RawConfigParser()
config.read(args.config)

## make some global vars here
# Serial device
DEVICE   = config.get('device', 'path')      or '/dev/serial/by-id/usb-Prolific_Technology_Inc._USB-Serial_Controller-if00-port0'
BAUD     = config.getint('device', 'baud')   or 57600

HOST  = config.get('publish', 'host')        or 'sjmf.in' 
PORT  = config.getint('publish', 'port')     or 61613
USER  = config.get('publish', 'user')        or 'pi'
PASS  = config.get('publish', 'pass')        or 'raspberry'
TOPIC = config.get('publish', 'topic')       or '/topic/ccost' 

# Log file
LOGDIR   = '/home/sam/log/readSerial/%Y-%m-%d/'
LOGFILE  = '%Y-%m-%d-%H-00-00.xml'

# Add error logging
log = logging.getLogger('stomp.py')
strh = logging.StreamHandler()
strh.setLevel(logging.DEBUG)
log.addHandler(strh)

#logging.basicConfig(level=logging.DEBUG)

# Main loop variable
running = True

## Function to make a deep directory
def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc: # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else: raise

## Main class
def main():
    s=Client(host=HOST, port=PORT)
    s.connect(USER, PASS)
    
    ## attempt to open serial port (or die)
    ser = serial.Serial(DEVICE, BAUD)
    if False:
        ser.close()
        sys.exit(1)
    
    prog = re.compile("src>([^<]+).+dsb>([^<]+).+time>([^<]+).+tmpr>([^<]+).+sensor>([^<]+).+id>([^<]+).+type>([^<]+).+watts>([^<]+)")
    hist = re.compile('<hist>')

    while running:
        ## read from ACM0
        line = ser.readline()
        ## log to disk
        # build filename from date/time
        path = datetime.now().strftime(LOGDIR)
        mkdir_p(path)
        path = path + datetime.now().strftime(LOGFILE)
        with open(path, 'a+') as f:
            f.write(line)
            f.close

        ## echo XML packet

        ## Check for history packets
        if hist.search(line):
            if args.verbosity > 0:
                print 'ignoring history packet'
            continue

        if args.verbosity > 0:
            print line

        ## convert to JSON
        m = prog.search(line)

        if m is None:
            print 'No match- something went wrong?'
            continue

        json = '{' + \
            '"Source":"'         + m.group(1) + '",' + \
            '"DaysSinceBirth":"' + m.group(2) + '",' + \
            '"Time":"'           + m.group(3) + '",' + \
            '"Temperature":"'    + m.group(4) + '",' + \
            '"Sensor":"'         + m.group(5) + '",' + \
            '"ID":"'             + m.group(6) + '",' + \
            '"Type":"'           + m.group(7) + '",' + \
            '"Watts":"'          + m.group(8) + '"'  + \
        '}'

        ## send STOMP frame
        s.put(json, destination=TOPIC)

    sock.close()
    s.disconnect()


if __name__ == "__main__":
    main()

