#!/bin/python3

import io
import logging
import datetime
import socketserver
import threading
import time
from http import server
from picamera2 import Picamera2
from picamera2.encoders import JpegEncoder, H264Encoder
from picamera2.outputs import FileOutput

PAGE = """\
<html>
<head>
<title>Security Portal CCTV Surveillance Camera</title>
<link rel="icon" type="image/png" href="favicon.png">
    <script type="text/javascript">
    <!--
        function sendRecordRequest() {
            var req = new XMLHttpRequest();
            req.open("GET", "/record", true);
            req.send();
        }
    //-->
    </script>
</head>
<body>
    <center>
       <h1>Security Portal CCTV Surveillance Camera</h1>
       <img src="stream.mjpg" width="640" height="480" id="still"/>
       <p>
       <button id="record" type="button" onclick="sendRecordRequest()">Record Something suspicious</button>
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
                logging.warning('Removed streaming client %s: %s', self.client_address, str(e))
        elif self.path == '/record':
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write("Starting suspicious recording!".encode('utf-8'))
            threading.Thread(target=recCam).start()
        else:
            self.send_error(404)
            self.end_headers()

class StreamingServer(socketserver.ThreadingMixIn, server.HTTPServer):
    allow_reuse_address = True
    daemon_threads = True

camera = Picamera2()

stream_config = camera.create_video_configuration(
    main={"size": (640, 480), "format": "RGB888"},
    lores={"size": (640, 480), "format": "YUV420"},
    raw={"size": (640, 480)},
    display=None
)

camera.configure(stream_config)
encoder = JpegEncoder()
output = StreamingOutput()
camera.start_recording(encoder, FileOutput(output))

def recCam():
    global camera

    date = datetime.datetime.now().strftime('%m-%d-%Y_%H.%M.%S')
    team = "Cam1"
    rec_file = '/tmp/FTP/recordings/' + team + '_' + date + '.h264'

    # Start recording while keeping the stream running
    encoder_recorder = H264Encoder(10000000)
    camera.start_encoder(encoder_recorder, FileOutput(rec_file))
    time.sleep(10)
    camera.stop_encoder(encoder_recorder)

try:
    address = ('', 8000)
    server = StreamingServer(address, StreamingHandler)
    server.serve_forever()
finally:
    camera.stop_recording()
