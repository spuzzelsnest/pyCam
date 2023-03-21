from js import document
from js import Blob
from js import URL

import picamera
import socketserver
from http import server
from time import sleep


PAGE="""\
    <html>
    <head>
    <title>HAKvision</title>
    <script type="text/javascript"><!--
 function reloadimg(){
    document.getElementById('still').src = 'still.jpg?' + (new Date()).getTime();
    setTimeout('reloadimg()',5000)
}
//--></script>
</head>
<center>
<body onLoad="javascript:reloadimg();">
<h1>PiCamera Still Capture Demo</h1>
<img src="still.jpg" width="1280" height="720" id="still"/>
<button id="record" type="button" onclick="record()">Record Something suspicious</button>
</center>
</body>
</html>
"""

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
                camera.rotation = 180
                self.send_header('Content-Type', 'image/jpeg')
                self.end_headers()
                camera.capture(self.wfile, format='jpeg')
        else:
            self.send_error(404)
            self.end_headers()

class StreamingServer(socketserver.ThreadingMixIn, server.HTTPServer):
    allow_reuse_address = True
    daemon_threads = True

def recording():
   camera = PiCamera()
   camera.rotation = 180
   camera.resolution = (1024, 768)
   camera.start_preview()
   camera.annotate_text = "PiCAM is on"

   camera.start_recording('/home/ggm/Shared/video.h264')
   sleep(15)
   camera.stop_recording()


record = document.getElementById("record")
record.addEventListener("click", pyodide.create_proxy(download_handler))

address = ('', 8000)
server = StreamingServer(address, StreamingHandler)
server.serve_forever()
