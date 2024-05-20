#!/bin/python3

import io, time, datetime, threading, socket

from picamera2 import Picamera2
from picamera2.encoders import H264Encoder
from picamera2.outputs import FileOutput

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

#class StreamingOutput(io.BufferedIOBase):
#    def __init__(self):
#        self.frame = None
#        self.condition = threading.Condition()
#
#    def write(self, buf):
#        with self.condition:
#            self.frame = buf
#            self.condition.notify_all()

def stream_video(picam2):
    sock.connect(("192.168.100.66", 8000))
    stream = sock.makefile("wb")
    output = FileOutput(stream)
    #output = StreamingOutput()
    #picam2.start_recording(H264Encoder(), FileOutput(output))

def recCam(picam2, filename):
    video_config = picam2.create_video_configuration()
    picam2.configure(video_config)
    encoder = H264Encoder(10000000)
    picam2.start_recording(encoder, filename)
    time.sleep(10)
    picam2.stop_recording()

def main():
    picam2 = Picamera2()
    config = picam2.create_video_configuration(main={"size": (640, 480), "format": "RGB888"})
    picam2.configure(config)

    stream_thread = threading.Thread(target=stream_video, args=(picam2,))
    stream_thread.start()

    date = datetime.datetime.now().strftime('%m-%d-%Y_%H.%M.%S')
    secret = "test2-secret"
    team = "testTeam"
    recFile = '/tmp/FTP/recordings/'+ team +'_'+ date +'.h264'

    record_thread = threading.Thread(target=recCam, args=(picam2, recFile))
    record_thread.start()

    # Join threads to ensure proper cleanup
    stream_thread.join()
    record_thread.join()

    picam2.stop_preview()
    picam2.close()

if __name__ == "__main__":
    main()