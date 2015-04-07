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
from stompy.simple import Client as StompClient
import sys
import signal
import time
import json


## Argument parsing from command line
parser = argparse.ArgumentParser(description='Read data from the serial device located at the path specified')

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
LOGGING     = config.getboolean('publish', 'log')
LOGDIR      = config.get('publish', 'logdir')
LOGDIR      = LOGDIR + '%Y-%m-%d/'
LOGFILE     = '%Y-%m-%d-%H-00-00.xml'


# Main loop variable
running = True

# Signal handler for clean exit
def signal_handler(signum, frame):
    running = False
    print "Exiting on interrupt..."

signal.signal(signal.SIGINT, signal_handler)


## Function to make a deep directory (for logging)
def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc: # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else: raise

# The LineTransform class can be subclassed to specify a transform on a given
# data source- for example, transforming XML or CSV to JSON
class LineTransform:
    def __init__(self):
        self.excludes = []
        self.transforms = []
    
    # Add a regex to exclude matching data
    def addExclude(self, regex):
        compiled = re.compile(regex)
        self.excludes.append(compiled)

    # Check if a line matches any added excludes
    def matchExcludes(self, line):
        for regex in self.excludes:
            if regex.search(line) and args.verbosity > 0:
                print "Dropping line as it matched an excluded regex"
                return True

        return False

    # Add a transform to modify data
    def addTransform(self, fnPtr):
        self.transforms.append(fnPtr)
    
    # Run through the transforms in the order they were added. 
    def runTransforms(self, line):
        for transform in self.transforms:
            if line != None:
                line = transform(line)
            else:
                break

        return line


# Take an XML-formatted CurrentCost packet, and transform it to JSON
def currentCostTransform(line):
    prog = re.compile("src>([^<]+).+dsb>([^<]+).+time>([^<]+).+tmpr>([^<]+).+sensor>([^<]+).+id>([^<]+).+type>([^<]+).+watts>([^<]+)")
    
    m = prog.search(line)

    if m is None:
        print 'No match- something went wrong?'
        return None

    return json.dumps({
        'Source'         : m.group(1),
        'DaysSinceBirth' : m.group(2),
        'Time'           : m.group(3),
        'Temperature'    : m.group(4),
        'Sensor'         : m.group(5),
        'ID'             : m.group(6),
        'Type'           : m.group(7),
        'Watts'          : m.group(8)
    }, separators=(',', ':'))


# Main function
def main():
    
    stomp=StompClient(STOMP_HOST, STOMP_PORT)
    stomp.connect(STOMP_USER, STOMP_PASS)
    
    ## attempt to open serial port (or die)
    ser = serial.Serial(DEVICE, BAUD)
    if False:
        ser.close()
        sys.exit(1)
  
    # Setup transform
    lformatter = LineTransform()
    lformatter.addExclude('<hist>')
    lformatter.addTransform(currentCostTransform)
    
    while running:
        # read from serial
        line = ser.readline()
        
        # Check if excluded
        if lformatter.matchExcludes(line) == True:
            continue

        # Transform to expected format
        line = lformatter.runTransforms(line)
        if line == None:
            continue
        
        ## send STOMP frame
        stomp.put(line, destination=PUB_TOPIC)
        
        # log to disk
        if LOGGING:
            # build filename from date/time
            path = datetime.now().strftime(LOGDIR)
            mkdir_p(path)
            path = path + datetime.now().strftime(LOGFILE)
            with open(path, 'a+') as f:
                f.write(line)
                f.close

        # Print (in verbose mode)
        if args.verbosity > 0:
            print line

    ser.close()
    stomp.disconnect()


if __name__ == "__main__":
    main()

