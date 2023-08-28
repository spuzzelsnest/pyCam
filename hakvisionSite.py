#!/bin/python3

import sys, picamera, datetime
import socketserver
from http import server
from time import sleep

# VARS
date = datetime.datetime.now().strftime('%m-%d-%Y_%H.%M.%S')
recFile = '/home/hikvision/FTP/recording' + date + '.h264'
secret = str(sys.argv[1:])

PAGE="""\
<html>
  <head>
    <title>HAKvision</title>
    <link rel="icon" type="image/png" href="favicon.png">
    <script type="text/javascript">
    <!--
	function reloadIMG(){
   	    document.getElementById('still').src = 'still.jpg?' + (new Date()).getTime();
            setTimeout('reloadimg()',5000);
        }

        function buttonClick(){
            alert("Starting suspicious recording");
            startRecording();
        }

        function sendRecordRequest() {
            var xhr = new XMLHttpRequest();
            xhr.open("GET", "/start_record", true);  // Specify the route on the server
            xhr.send();
        }
    //-->
    </script>
  </head>
  <body onLoad="javascript:reloadIMG();">
    <center>
       <h1>PiCamera Still Capture Demo</h1>
       <img src="still.jpg" width="1280" height="720" id="still"/>
       <p>
       <button id="record" type="button" onclick="record()">Record Something suspicious</button>
    </center>
  </body>
</html>
"""

def recCam():
    camera = PiCamera()
    camera.rotation = 0
    camera.resolution = (1024, 768)
    camera.start_preview()
    camera.annotate_text = secret
    camera.start_recording(recFile)
    sleep(5)
    camera.stop_recording()

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
        elif self.path.startswith('/still.jpg'):
            self.send_response(200)
            self.send_header('Age', 0)
            self.send_header('Cache-Control', 'no-cache, private')
            self.send_header('Pragma', 'no-cache')
            with picamera.PiCamera(resolution='1280x720') as camera:
                camera.rotation = 0
                self.send_header('Content-Type', 'image/jpeg')
                self.end_headers()
                camera.capture(self.wfile, format='jpeg')
        elif self.path == '/start_recording':
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end.headers()
            self.wfile.write("Starting suspicious recording!".encode('utf-8'))
            recCam()
        else:
            self.send_error(404)
            self.end_headers()

class StreamingServer(socketserver.ThreadingMixIn, server.HTTPServer):
    allow_reuse_address = True
    daemon_threads = True

address = ('', 8000)
server = StreamingServer(address, StreamingHandler)
server.serve_forever()
