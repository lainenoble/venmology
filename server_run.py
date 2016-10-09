#!/usr/bin/python
from flaskapp import app
from gevent.pywsgi import WGSIServer
http_server = WSGIServer(('',80),app)
http_server.serve_forever()
