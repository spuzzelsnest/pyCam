#!/bin/python3

import io
import logging
import datetime
import socketserver
import threading
import time

from http import server
from picamera2 import Picamera2
from picamera2.encoders import MJPEGEncoder, H264Encoder
from picamera2.outputs import FileOutput

PAGE="""\
<html>
<head>
<title>Security Portal CCTV Surveillance Camera</title>
<link rel="icon" type="image/png" href="favicon.png">
    <script type="text/javascript">
    <!--
        function record(){
            alert("Starting suspicious recording");
        }

        function sendRecordRequest() {
            record();
            var xhr = new XMLHttpRequest();
            xhr.open("GET", "/record", true);  // Specify the route on the server
            xhr.send();
        }
    //-->
    </script>
</head>
<body>
    <center>
       <h1>Security Portal CCTV Surveillance Camera</h1>
       <img src="stream.mjpg" width="720" height="480" id="still"/>
       <p>
       <button id="record" type="button" onclick="sendRecordRequest()">Record Something suspicious</butto>
    </center>
  </body>
</html>
"""

class StreamingOutput(io.BufferedIOBase):
    def __init__(self):
        self.frame = None
        self.condition = threading.Condition()

    def write(self, buf):
        with self.condition:
            self.frame = buf
            self.condition.notify_all()


class StreamingHandler(server.BaseHTTPRequestHandler):
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
                    with outputStream.condition:
                        outputStream.condition.wait()
                        frame = outputStream.frame
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
        else:
            self.send_error(404)
            self.end_headers()


class StreamingServer(socketserver.ThreadingMixIn, server.HTTPServer):
    allow_reuse_address = True
    daemon_threads = True


stream = Picamera2()
configStream = stream.create_video_configuration(main={"size": (640, 480), "format": "RGB888"})
stream.configure(configStream)
encoderStream = MJPEGEncoder()
outputStream = StreamingOutput()

stream.start_recording(encoderStream, FileOutput(outputStream))

def recCam():

    date = datetime.datetime.now().strftime('%m-%d-%Y_%H.%M.%S')
    team = "Cam1"
    recFile = '/tmp/FTP/recordings/'+ team +'_'+ date +'.h264'
    recorder = Picamera2()
    configRecorder = recorder.create_video_configuration()
    recorder.configure(configRecorder)
    encoderRecorder = H264Encoder(10000000)
    recorder.start_recording(encoderRecorder, recFile)
    time.sleep(10)
    recorder.stop_recording()

try:
    address = ('', 8000)
    server = StreamingServer(address, StreamingHandler)
    server.serve_forever()

finally:
    stream.stop_recording()