# homeSec

homeSec is a Raspberry Pi App where a connected webcam sends a picture on command to an email address.

## Get Started
### Installing

Run the preperation file first. This will install msmtp-mta - fswebcam - which are needed for the program to run. 
This will add the additional software and add the user to the necessary groups. It will ask for sudo passwords where needed.

```
./preps.sh
```

### MSMTP config

msmtp is used for sending emails. Make sure this config file is in the home directory of the user who will be sending the emails.


```
#~/.msmtprc

# Set default values for all following accounts.

defaults
auth            on
tls             on
tls_certcheck   off
#tls_trust_file         /etc/ssl/certs/ca-certificates.crt
logfile         ~/.msmtp.log

account gmail
host 		smtp.gmail.com
from 		<user>@gmail.com
auth 		on
user 		<user>
passwordeval gpg -d ~/.msmtp-gmail.gpg

# Set a default account
account default : gmail

```

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
