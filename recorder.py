#!/usr/bin/python3

import sys
import psutil
from picamera import PiCamera
from time import sleep

print(sys.argv[1:])

def checkProcess(processName):

    #Iterate over the all the running process
    for proc in psutil.process_iter():
        try:
            # Check if process name contains the given name string.
            if processName.lower() in proc.name().lower():
                proc.kill()
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return False;


def recCam():
    rec_file="/home/hikvision/FTP/recording.h264"

    camera = PiCamera()
    camera.rotation = 180
    camera.resolution = (1024, 768)
    camera.annotate_text = str(sys.argv[1:])
    camera.start_recording(rec_file)
    sleep(5)
    camera.stop_recording()
    camera.close()

if checkProcess('motion'):
    print('Yes a motion process was running and we tried to stop it')
    recCam()
else:
    print('No motion process was running')
    recCam()
