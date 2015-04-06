# logging-v2
Read from IoT devices connected with serial, publish to a message queue, and log 'em to mongoDB

Best used with devices which spew valid JSON. ;)

Partial rewrite of previous IoT logging infrastructure using STOMP as the MQ carrier protocol

## Dependencies (python modules)
Pay attention to the version!

- [`stompy`](http://packages.python.org/stompy) - STOMP client implementation (v 0.2.9)
- [`pymongo`](https://api.mongodb.org/python/2.8) - MongoDB python driver (v 2.8)
- [`pyserial`](http://pythonhosted.org//pyserial) - Serial libs (v 2.6)
