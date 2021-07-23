#!/bin/bash

dump='/home/ggm/Pictures/homeSec'
zips='/home/ggm/Pictures/sendFiles'
date=$(date +"%Y-%m-%d_%H%M")
email='j.mpdesmet@protonmail.com'
mkdir -p $dump
mkdir -p $zips

echo '-------------------------------------'
echo '|Zipping files and removing org File|'
echo '-------------------------------------'
cd $dump
zip -r $zips/homeSec_$date.zip *
rm $dump/*

echo '--------------------------------------------------------'
echo '|sending' $zips/homeSec_$date.zip to $email
echo '---------------------------------------------------------'

echo "neuze neuze" | mutt -s "Motion Detected" -a $zips/homeSec_$date.zip -- $email
