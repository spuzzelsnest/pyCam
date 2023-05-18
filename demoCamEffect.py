#!/bin/python3

from picamera import PiCamera
from time import sleep

camera = PiCamera()

camera.start_preview()

for effect in camera.IMAGE_EFFECTS:
    camera.image_effect = effect
    camera.annotate_text = "Effect: %s" % effect
    sleep(5)

for i in range(100):
    camera.annotate_text = "Contrast: %s" % i
    camera.contrast = i
    sleep(0.2)

for i in range(100):
    camera.annotate_text = "Brightness: %s" % i
    camera.brightness = i 
    sleep(0.2)

for exposure in camera.AWB_MODES:
    camera.annotate_text = "Exposure: %s" % i
    camera.awb_mode = exposure
    sleep(5)




