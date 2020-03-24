#!/bin/bash

sudo mkdir /mnt/ramdisk
echo 'tmpfs       /mnt/ramdisk tmpfs   nodev,nosuid,noexec,nodiratime,size=100M   0 0' | sudo tee -a /etc/fstab
sudo mount -a