#!/usr/bin/python3
# REQUIREMENTS
# pip3 install psutil picamera

import os, sys, socket, errno
import psutil
import datetime

from picamera import PiCamera
from time import sleep
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

#VARS
date = datetime.datetime.now().strftime('%m-%d-%Y_%H.%M.%S')
recFile = '/home/hikvision/FTP/recording' + date + '.h264'
secret = str(sys.argv[1:])

def recCam():
    camera = PiCamera()
    camera.rotation = 0
    camera.resolution = (1024, 768)
    camera.start_preview()
    camera.annotate_text = secret
    camera.start_recording(recFile)
    sleep(5)
    camera.stop_recording()

def testPort(port):
    try:
        s.bind(('127.0.0.1', port))
    except socket.error as e:
        if e.errno == errno.EADDRINUSE:
            print('Port is already in use, we need to close it')
            os.system('sudo /bin/systemctl stop motion.service')
            sleep(2)
            print('The service should be stopped now')
            return False
        else:
            # something else raised the socket.error exception
            print(e)
    s.close()
if testPort(8081):
    print('Yes a motion process is running ')
    testPort(8081)
else:
    print('Starten Suspicious Recording', secret)
    recCam()
    print('... Recording Done ...')
    sleep(2)
    print('Restarting Live View')
    os.system('sudo motion -b')
    sleep(2)
    print('Live View Restarted')
