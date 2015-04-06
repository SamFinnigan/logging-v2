#!/usr/bin/python
#
# STOMP to MongoDB bridge
# Using configuration file for list of sites
# This script should re-load if the config changes
#

import time
import ConfigParser
import argparse
from stompy.simple import Client as StompClient
import json
from pymongo import MongoClient

# Parse program arguments
parser = argparse.ArgumentParser(description="Subscribe to message queues and log into MongoDB collections")

parser.add_argument('-v','--verbose', action='count', dest='verbosity', help='verbose output', default=0)
parser.add_argument('-c','--config',  action="store",  dest='config',    type=str,  help='Configuration File', default='config.ini')

args = parser.parse_args()

## Read config file and set global vars
config = ConfigParser.RawConfigParser()
config.read(args.config)

STOMP_HOST  = config.get('stomp', 'host')       or 'sjmf.in' 
STOMP_PORT  = config.getint('stomp', 'port')    or 61613
STOMP_USER  = config.get('stomp', 'user')       or 'pi'
STOMP_PASS  = config.get('stomp', 'pass')       or 'raspberry'

MONGO_HOST = config.get('subscribe', 'host')    or 'localhost'
MONGO_PORT = config.getint('subscribe', 'port') or 27017

SITE_LIST = config.get('subscribe', 'list')


# Read in json sites config file
def readconf_json(sites_list):
    with open(sites_list) as f:
         return json.load(f)

# Read in sites list from mysql
# Not yet implemented!
def readconf_mysql():
    pass

# Main program loop
def main():
    # Connect to mongoDB
    mongo = MongoClient(MONGO_HOST, MONGO_PORT)

    # Connect to STOMP MQ
    stomp = StompClient(STOMP_HOST, STOMP_PORT)
    stomp.connect(STOMP_USER, STOMP_PASS)
    
    # Read in JSON format sites list
    sites = readconf_json(SITE_LIST)
    dest = {}

    for s in sites:
        # Subscribe to queues
        stomp.subscribe(s['src'])
    
        # Create mapping of stomp destinations to mongo collections
        # Duplicate entries are overwritten (for now)
        dest[s['src']] = [ 
            s['dst'].split('.')[0], 
            s['dst'].split('.')[1] 
        ]
        
    # Message RX loop
    while True:
        # Recieve message from subscribed queue
        message = stomp.get() 
        #print message.body
        
        src = message.headers['destination']
        dst_db = dest[src][0]
        dst_co = dest[src][1]
        
        # Insert message into configured mongo db.collection
        db = mongo[dst_db]
        co = db[dst_co]
        co.insert_one(message.body)

        #

        # Loop


if __name__ == "__main__":
    main()
