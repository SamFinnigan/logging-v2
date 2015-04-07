#!/usr/bin/python
#
# Configurable Serial to STOMP bridge 
# Author: Sam Mitchell Finnigan
# Based on code by Sebastian Mellor
#

import argparse
import ConfigParser
import json
import yaml
import io
from datetime import datetime
import os, errno
import re
import serial
from stompy.simple import Client as StompClient
import sys
import signal
import time

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
    'parsers_file': 'parsers.yml',
    'parser': None, 
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
PARSERS_FILE= config.get('publish', 'parsers_file')
PARSER      = config.get('publish', 'parser')

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


# GenericTransform specifies a process of transformation on a line of
# data, using a regex to split the line into groups which are output
# in the order they are specified
class GenericTransform:
    def __init__(self, regex, groups):
        self.regex = re.compile(regex)
        self.groups = groups

    def process(self, line):
        match = self.regex.search(line)

        if match is None:
            print 'No match- something went wrong?'
            return None
        
        final = dict( zip(self.groups, list( match.groups() )) )
        return json.dumps( final, separators=(',', ':') )


# The LineParser class specifies transforms on a given line as read from a
# data source- for example, to transform XML or CSV into JSON
class LineParser:
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
    def addTransform(self, genericTransform):
        self.transforms.append(genericTransform)
    
    # Run through the transforms in the order they were added. 
    def runTransforms(self, line):
        for transform in self.transforms:
            if line != None:
                line = transform.process(line)
            else:
                break

        return line

    # Configure self with a parser from yaml config file
    def loadConfiguration(self, find_parser, config):
        with open(config, 'r') as stream:
            parser_list = yaml.load(stream)
      
        parser = []
        for p in parser_list['parsers']:
            if p['name'] == find_parser:
                parser = p
        
        transform = GenericTransform(parser['search'], parser['groups'])
        self.addTransform(transform)


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
    lformatter = LineParser()
    lformatter.loadConfiguration(PARSER, PARSERS_FILE)

    while running:
        # read from serial
        line = ser.readline()
       
        if args.verbosity > 2:
            print line

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

