#!/bin/bash

programs=(ssmtp fswebcam zip mail)
dump='/home/jack/sjan/homeSec/pix'
zips='/home/jack/sjan/homeSec/sendFiles'
date=$(date +"%Y-%m-%d_%H%M")
email='j.mpdesmet@gmail.com'

mkdir -p $dump
mkdir -p $zips

apt-get update

for program in "${programs[@]}"; do
    if ! command -v "$program" > /dev/null 2>&1; then
        apt-get install "$program" -y
    fi
done


fswebcam -r 1280x720 --no-banner $dump/$date.jpg

cd $dump
zip -r $zips/homeSec_$date.zip *
cd ..
rm $dump/*
echo "neuze neuze" | mail -s "Motion Detected" $email -A $zips/homeSec_$date.zip


echo 'message mailed'
