# logging-v2
Read from IoT devices connected with serial, publish to a message queue, and log 'em to mongoDB

Almost total rewrite of previous IoT logging infrastructure using STOMP as the MQ carrier protocol

## Dependencies (python modules)
Pay attention to the version! Things might change and break stuff.

- [`stompy`](http://packages.python.org/stompy) - STOMP client implementation (v 0.2.9)
- [`pymongo`](https://api.mongodb.org/python/2.8) - MongoDB python driver (v 2.8)
- [`pyserial`](http://pythonhosted.org//pyserial) - Serial libs (v 2.6)
- [`PyYAML`](http://pyyaml.org) - Python YAML library (v 3.10)
