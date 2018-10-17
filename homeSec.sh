#!/bin/bash
user=$(whoami)
groups=( mail video motion )
programs=( ssmtp fswebcam zip mail motion )
dump='pix'
zips='sendFiles'
date=$(date +"%Y-%m-%d_%H%M")
email=j.mpdesmet@gmail.com

mkdir -p $dump
mkdir -p $zips


echo hi $user test, test
echo --------------------------
for i in "${groups[@]}"; do
    if getent group $i  | grep &>/dev/null "\b${user}\b"; then
        echo Member of group $i
    else
        echo No Member of group $i
	sudo adduser $user $i
    fi
done


sudo apt-get update

for program in "${programs[@]}"; do
    if ! command -v "$program" > /dev/null 2>&1; then
        sudo apt-get install "$program" -y
    fi
done

echo ---------------
echo taking picture
echo ---------------

fswebcam -r 1280x720 --no-banner $dump/$date.jpg

echo --------------
echo zipping files
echo --------------
cd $dump
zip -r $zips/homeSec_$date.zip *
cd ..
echo ---------------
echo removing files
echo ---------------

rm $dump/*

echo --------------------------------------------------------
echo sending $zips/homeSec_$date.zip to $email
echo ---------------------------------------------------------

echo "neuze neuze" | mail -s "Motion Detected" $email -A $zips/homeSec_$date.zip

