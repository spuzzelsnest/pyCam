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
import signal

# Define configuration parameters
PORT = 8000
STREAM_RESOLUTION = (640, 480)
RECORDING_DURATION = 10

# HTML page content
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
    def __init__(self, *args, output=None, **kwargs):
        self.output = output
        super().__init__(*args, **kwargs)

    def do_GET(self):
        if self.path == '/':
            self.send_response(301)
            self.send_header('Location', '/index.html')
            self.end_headers()
        elif self.path == '/index.html':
            self._serve_html_page()
        elif self.path == '/favicon.png':
            self._serve_favicon()
        elif self.path == '/stream.mjpg':
            self._serve_video_stream()
        elif self.path == '/record':
            self._start_recording()
        else:
            self.send_error(404)
            self.end_headers()

    def _serve_html_page(self):
        content = PAGE.encode('utf-8')
        self._send_response(content, 'text/html')

    def _serve_favicon(self):
        with open('favicon.png', 'rb') as f:
            content = f.read()
        self._send_response(content, 'image/png')

    def _serve_video_stream(self):
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

    def _send_response(self, content, content_type):
        self.send_response(200)
        self.send_header('Content-type', content_type)
        self.send_header('Content-Length', len(content))
        self.end_headers()
        self.wfile.write(content)

    def _start_recording(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write("Starting suspicious recording!".encode('utf-8'))
        threading.Thread(target=self._record).start()

    def _record(self):
        date = datetime.datetime.now().strftime('%m-%d-%Y_%H.%M.%S')
        team = "Cam1"
        rec_file = '/tmp/FTP/recordings/' + team + '_' + date + '.h264'

        # Start recording while keeping the stream running
        encoder_recorder = H264Encoder(10000000)
        camera.start_encoder(encoder_recorder, FileOutput(rec_file))
        time.sleep(RECORDING_DURATION)
        camera.stop_encoder(encoder_recorder)
        logging.info("Recording Stopped")

class StreamingServer(socketserver.ThreadingMixIn, server.HTTPServer):
    def __init__(self, *args, output=None, **kwargs):
        self.output = output
        super().__init__(*args, **kwargs)

    allow_reuse_address = True
    daemon_threads = True

def signal_handler(signal, frame):
    logging.info("Shutting down server...")
    server.shutdown()
    camera.stop_recording()

def main():
    global server
    global camera
    global output

    # Initialize camera
    camera = Picamera2()
    stream_config = camera.create_video_configuration(main={"size": STREAM_RESOLUTION, "format": "RGB888"}, lores={"size": STREAM_RESOLUTION, "format": "YUV420"}, raw={"size": STREAM_RESOLUTION}, display=None)
    camera.configure(stream_config)
    encoder = JpegEncoder()
    output = StreamingOutput()
    camera.start_recording(encoder, FileOutput(output))

    # Start the server
    address = ('', PORT)
    server = StreamingServer(address, StreamingHandler, output=output)
    server_thread = threading.Thread(target=server.serve_forever)

    # Register signal handler
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Start server
    try:
        logging.info(f"Starting server on port {PORT}...")
        server_thread.start()
        server_thread.join()
    finally:
        logging.info("Shutting down camera...")
        camera.stop_recording()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
