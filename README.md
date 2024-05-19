

# PyCam on Raspberry Pi 4B
## Info

This script is build with python 3 modules picamera, psutil and it can be installed with pip3.

## Prerequisites

### Raspberry Pi and Camera

If the camera is not detected right away by the raspberry pi, check the file /boot/firmware/config.txt

```
sudo nano /boot/firmware/config.txt

 # verify the following enteries

	camera_auto_detect=1
	#dtoverlay=vc4-kms-v3d
	#dtoverlay=imx219
	#disable_fw_kms_setup=1
	start_x=1
	gpu_mem=512
	disable_camera_led=1

```

Once booted back into the os, make sure the following apps are available. 

```
sudo apt update
sudo apt full-update -y
sudo apt install -y python3 python3-picamera2

```

Test the camera. 

```
vcgencmd get_camera
supported=1 detected=0, libcamera interfaces=1

libcamera-hello
[0:16:12.667298543] [1165]  INFO Camera camera_manager.cpp:284 libcamera v0.2.0+120-eb00c13d
[0:16:12.705065820] [1168]  WARN RPiSdn sdn.cpp:40 Using legacy SDN tuning - please consider moving SDN inside rpi.denoise
[0:16:12.707286665] [1168]  INFO RPI vc4.cpp:446 Registered camera /base/soc/i2c0mux/i2c@1/imx477@1a to Unicam device /dev/media1 and ISP device /dev/media3
[0:16:12.707367134] [1168]  INFO RPI pipeline_base.cpp:1102 Using configuration file '/usr/share/libcamera/pipeline/rpi/vc4/rpi_apps.yaml'
Preview window unavailable
Mode selection for 2028:1520:12:P
    SRGGB10_CSI2P,1332x990/0 - Score: 3456.22
    SRGGB12_CSI2P,2028x1080/0 - Score: 1083.84
    SRGGB12_CSI2P,2028x1520/0 - Score: 0
    SRGGB12_CSI2P,4056x3040/0 - Score: 887
Stream configuration adjusted
[0:16:12.772818852] [1165]  INFO Camera camera.cpp:1183 configuring streams: (0) 2028x1520-YUV420 (1) 2028x1520-SBGGR12_CSI2P
[0:16:12.773210788] [1168]  INFO RPI vc4.cpp:621 Sensor: /base/soc/i2c0mux/i2c@1/imx477@1a - Selected sensor format: 2028x1520-SBGGR12_1X12 - Selected unicam format: 2028x1520-pBCC
#0 (0.00 fps) exp 9994.00 ag 1.11 dg 1.09
...
``` 

### Run the App

Clone the repository and change into the directory.

```
cd pyCam




