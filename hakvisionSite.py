#!/bin/python3

import sys, picamera, datetime
import socketserver
from http import server
from time import sleep

# VARS
date = datetime.datetime.now().strftime('%m-%d-%Y_%H.%M.%S')
secret = str(sys.argv[1:])
rec_counter = 1

PAGE="""\
<html>
  <head>
    <title>HAKvision</title>
    <link rel="icon" type="image/png" href="favicon.png">
    <script type="text/javascript">
    <!--
        var isPaused = false;

	function reloadIMG(){
   	    document.getElementById('still').src = 'still.jpg?' + (new Date()).getTime();
            setTimeout('reloadIMG()',5000);
        }

        function toggleCamera() {
             isPaused = !isPaused;
             var imgElement = document.getElementById("still");
             if (isPaused) {
                 imgElement.style.display = "none";  // Hide the image
             } else {
                 imgElement.style.display = "block"; // Show the image
             }
        }

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
  <body onLoad="javascript:reloadIMG();">
    <center>
       <h1>HAKvision</h1>
       <img src="still.jpg" width="1280" height="720" id="still"/>
       <p>
       <button id="record" type="button" onclick="sendRecordRequest()">Record Something suspicious</button>
    </center>
  </body>
</html>
"""

def recCam():
    global rec_counter
    recFile = f'/home/hikvision/FTP/recording/{rec_counter}_{date}.h264'
    with picamera.PiCamera() as camera:
        camera.rotation = 0
        camera.resolution = (1024, 768)
        camera.start_preview()
        camera.annotate_text = secret
        camera.start_recording(recFile)
        rec_counter += 1
        sleep(5)
        camera.stop_recording()

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
        elif self.path.startswith('/still.jpg'):
            if not StreamingHandler.paused:
                self.send_response(200)
                self.send_header('Age', 0)
                self.send_header('Cache-Control', 'no-cache, private')
                self.send_header('Pragma', 'no-cache')
                with picamera.PiCamera(resolution='1280x720') as camera:
                    camera.rotation = 0
                    self.send_header('Content-Type', 'image/jpeg')
                    self.end_headers()
                    camera.capture(self.wfile, format='jpeg')
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

address = ('', 8000)
server = StreamingServer(address, StreamingHandler)
server.serve_forever()
