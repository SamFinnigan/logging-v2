#!/usr/bin/python
#
# Configurable Serial to STOMP bridge 
# Author: Sam Mitchell Finnigan
# Based on code by Sebastian Mellor
#

import argparse
import ConfigParser
import io
from datetime import datetime
import os, errno
import re
import serial
from stompy.simple import Client
import sys
import time

from subprocess import Popen

## Argument parsing from command line
parser = argparse.ArgumentParser(description='Read data from the CurrentCost EnviR located at the serial device specified')

parser.add_argument('-v','--verbose', action="count",  dest='verbosity', help='verbose output', default=0)
parser.add_argument('-c','--config',  action="store",  dest='config',    type=str,  help='Configuration File', default='config.ini')

args = parser.parse_args()

## Read configuration file 
# (defaults are provided to ConfigParser constructor)
config = ConfigParser.RawConfigParser({
    'path' : '/dev/serial/by-id/usb-Prolific_Technology_Inc._USB-Serial_Controller-if00-port0',
    'baud' : 57600,
    'host' : 'localhost',
    'port' : 61613,
    'user' : 'pi',
    'pass' : 'raspberry',
    'topic': '/topic/ccost',
    'log'  : False,
    'logdir':'/var/log/'
})
config.read(args.config)

# Read in configuration from provided --config file
# Serial device
DEVICE      = config.get('device', 'path')
BAUD        = config.getint('device', 'baud')

# STOMP credentials
STOMP_HOST  = config.get('stomp', 'host')
STOMP_PORT  = config.getint('stomp', 'port')
STOMP_USER  = config.get('stomp', 'user')
STOMP_PASS  = config.get('stomp', 'pass')
PUB_TOPIC   = config.get('publish', 'topic')

# Log files
LOGGING  = config.getboolean('publish', 'log')
LOGDIR   = config.get('publish', 'logdir')
LOGDIR   = LOGDIR + '%Y-%m-%d/'
LOGFILE  = '%Y-%m-%d-%H-00-00.xml'

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
    s=Client(host=STOMP_HOST, port=STOMP_PORT)
    s.connect(STOMP_USER, STOMP_PASS)
    
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
        if LOGGING:
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
        s.put(json, destination=PUB_TOPIC)

    sock.close()
    s.disconnect()


if __name__ == "__main__":
    main()

