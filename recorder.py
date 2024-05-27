#!/usr/bin/python3

import sys, logging, socket, datetime, time

from picamera2 import Picamera2
from picamera2.encoders import H264Encoder
from picamera2.outputs import FileOutput

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

#VARS

camera = Picamera2()
RECORDING_DURATION = 10

date = datetime.datetime.now().strftime('%m-%d-%Y_%H.%M.%S')
secret = str(sys.argv[1])
team = str(sys.argv[2])
recFile = '/tmp/FTP/recordings/'+ team +'_'+ date +'.h264'

encoderRecorder = H264Encoder(10000000)

camera.start_encoder(encoderRecorder, FileOutput(recFile))
time.sleep(RECORDING_DURATION)
camera.stop_encoder(encoderRecorder)
logging.info("Recording Stopped")
