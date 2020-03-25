#!/bin/bash

pip3 install virtualenv --user
virtualenv env
source env/bin/activate

pip install -r requirements.txt

sudo mkdir /mnt/ramdisk
echo 'tmpfs       /mnt/ramdisk tmpfs   nodev,nosuid,noexec,nodiratime,size=100M   0 0' | sudo tee -a /etc/fstab
sudo mount -a

# Newest version needed for additional errors see: https://gitlab.mister-muffin.de/josch/img2pdf/issues/61
git clone http://gitlab.mister-muffin.de/josch/img2pdf.git
cd img2pdf
pip install .
