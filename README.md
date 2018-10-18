# homeSec

homeSec is a Raspberry Pi App where a connected webcam sends a picture on command to an email address.

## Getting Started

Download the project and unpack it. This App assumes you have a working ssmtp connection and are able to send e-mails from the Raspberry Pi.
You can verify this by checking the file

```
cat /etc/ssmtp/ssmtp.conf
```

### Installing

Run the preperation file first.

```
./preps.sh
```

This will add the additional software and add the user to the necessary groups. It will ask for sudo passwords where needed.
Best practice is to reboot after this.

```
sudo reboot
```

## Running the App

Run the program with the following command

```
./homeSec
```
It will ask you for you e-mail address to send the test file.

## Customisable Options

motion.sh can be added to the /etc/motion/motion.conf file in the section:

```
# Command to be executed when a motion frame is detected (default: none)
 on_motion_detected /bin/bash /[DIR LOCATIOON]/motion.sh
```
