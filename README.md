# homeSec

homeSec is a Raspberry Pi App where a connected webcam sends a picture on command to an email address when motion is detected.

## Get Started
### Installing

Run the preperation file first. This will install msmtp-mta - mutt - fswebcam - zip - mail - motion which are needed for the program to run. 
This will add the additional software and add the user to the necessary groups. It will ask for sudo passwords where needed.

```
./preps.sh
```

### MSMTP config

msmtp is used for sending emails. Make sure this config file is in the home directory of the user who will be sending the emails.

** if you are using a G Mail Account without OAUTH2, make sure "Less secure apps" is enabled for the account. Google reported that the option to send over "Less Secure Apps" will be deprecated in Feb 2020!


```
#~/.msmtprc

# Set default values for all following accounts.

defaults
tls             on
tls_starttls	on
tls_certcheck   off
tls_trust_file  /etc/ssl/certs/ca-certificates.crt
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

Set the right permissions for the file:

```
chmod 600 .msmtprc
```

To encrypt your account password you can use GPG to encrypt it.

If you haven't used GPG before you first need to run the following:

```
gpg --gen-key
```
create a file with the plain text password.

```
echo "MY SUPER SECRET GMAIL PASS" > plaintext.txt
```

Use next command to encrypt the file. Use the email address you used to create the account here.

```
gpg --encrypt -o .msmtp-gmail.gpg -r <user>@gmail.com plaintext.txt
```
Remove your plain text password file!! Also be aware that if you added the pass with echo, it is still in your .[shell]_history!
```
rm plaintext.txt
```
Best practice is to reboot after this.
```
sudo reboot
```
After the reboot you can check if the sending email from the command line is working by issuing the following command.
```
echo "This is the test message" | mutt -s "Testing mutt" <RECIPIENT EMAILL> 
```
If errors should come up, make sure gpg is properly connecting.
```
export GPG_TTY=$(tty)
```
## Running the App

Run the program with the following command

```
./homeSec
```
It will ask you for you e-mail address to send the test file.

## Customisable Options

In motion.sh change line 7 to add an email address to send the homesecurity files to.
If you want to use the motion option, add 'motion.sh' to the /etc/motion/motion.conf file in the section:

```
# Command to be executed when a motion frame is detected (default: none)
 on_motion_detected /bin/bash /[DIR LOCATIOON]/motion.sh
```
