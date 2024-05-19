#!/bin/python3

import sys, io, logging, datetime
import socketserver
from http import server
from time import sleep
from threading import Condition

from picamera2 import Picamera2
from picamera2.encoders import JpegEncoder
from picamera2.outputs import FileOutput

# VARS
date = datetime.datetime.now().strftime('%m-%d-%Y_%H.%M.%S')
secret = str(sys.argv[1:])
rec_counter = 1

picam2 = Picamera2()


PAGE="""\
<html>
  <head>
    <title>HAKvision</title>
    <link rel="icon" type="image/png" href="favicon.png">
  </head>
  <body onLoad="javascript:reloadIMG();">
    <center>
       <h1>HAKvision</h1>
       <img src="stream.mjpg" width="1280" height="720" id="still"/>
       <p>
       <button id="record" type="button" onclick="sendRecordRequest()">Record Something suspicious</button>
    </center>
  </body>
1024, 768</html>
"""

class StreamingOutput(io.BufferedIOBase):
    def __init__(self):
        self.frame = None
        self.condition = Condition()

    def write(self, buf):
        with self.condition:
            self.frame = buf
            self.condition.notify_all()

class StreamingHandler(server.BaseHTTPRequestHandler):
    paused = False

    def do_GET(self):
        if self.path == '/':
            self.send_response(301)
            self.send_header('Location', '/index.html')
            self.end_headers()
        elif self.path == '/index.html':
            content = PAGE.encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.send_header('Content-Length', len(content))
            self.end_headers()
            self.wfile.write(content)
        elif self.path == '/favicon.png':
            self.send_response(200)
            self.send_header('Content-Type', 'image/png')
            self.end_headers()
            with open('favicon.png', 'rb') as f:
                self.wfile.write(f.read())
        elif self.path == '/stream.mjpg':
            self.send_response(200)
            self.send_header('Age', 0)
            self.send_header('Cache-Control', 'no-cache, private')
            self.send_header('Pragma', 'no-cache')
            self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=FRAME')
            self.end_headers()
            try:
                while True:
                    with output.condition:
                        output.condition.wait()
                        frame = output.frame
                    self.wfile.write(b'--FRAME\r\n')
                    self.send_header('Content-Type', 'image/jpeg')
                    self.send_header('Content-Length', len(frame))
                    self.end_headers()
                    self.wfile.write(frame)
                    self.wfile.write(b'\r\n')
            except Exception as e:
                logging.warning(
                    'Removed streaming client %s: %s',
                    self.client_address, str(e))
        elif self.path == '/record':
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write("Starting suspicious recording!".encode('utf-8'))
            recCam()
        elif self.path == '/toggle_pause':
            StreamingHandler.paused = not StreamingHandler.paused
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(("Paused: " + str(StreamingHandler.paused)).encode('utf-8'))
            return
        else:
            self.send_error(404)
            self.end_headers()

class StreamingServer(socketserver.ThreadingMixIn, server.HTTPServer):
    allow_reuse_address = True
    daemon_threads = True


video_config = picam2.create_video_configuration(
    main={"size": (1280, 720), "format": "RGB888"},
    lores={"size": (1280, 720), "format": "YUV420"},
    raw={"size": (1280, 720)},
    display=None
)
output = StreamingOutput()
picam2.start_recording(JpegEncoder(), FileOutput(output))


address = ('', 8000)
server = StreamingServer(address, StreamingHandler)
server.serve_forever()
