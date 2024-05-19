#!/usr/bin/python3

# REQUIREMENTS
# pip3 install picamera2

import os, sys, socket, errno
import datetime

from picamera2 import Picamera2
from picamera2.encoders import H264Encoder
from time import sleep
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

#VARS
date = datetime.datetime.now().strftime('%m-%d-%Y_%H.%M.%S')
secret = str(sys.argv[1])
team = str(sys.argv[2])
recFile = '/tmp/FTP/recordings/'+ team +'_'+ date +'.h264'

def recCam():
    picam2 = Picamera2()
    video_config = picam2.create_video_configuration()
    picam2.configure(video_config)
    encoder = H264Encoder(10000000)
    picam2.start_recording(encoder, recFile)
    sleep(10)
    picam2.stop_recording()

def testPort(port):
    try:
        s.bind(('127.0.0.1', port))
    except socket.error as e:
        if e.errno == errno.EADDRINUSE:
            print('Port is already in use, we need to close it')
            os.system('kill $(lsof -t -i:8000) ')
            sleep(2)
            print('The service should be stopped now')
            return False
        else:
            # something else raised the socket.error exception
            print(e)
    s.close()

if testPort(8000):
    print('Yes a Streaming process is running ')
    testPort(8000)
else:
    print('Starten Suspicious Recording', secret)
    recCam()
    print('... Recording Done ...')
    sleep(2)
    print('Restarting Live View')
    os.system('python3 hakvisionSite.py')
    sleep(2)
    print('Live View Restarted')
