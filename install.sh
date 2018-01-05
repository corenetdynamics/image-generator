#!/usr/bin/env bash

sudo apt update && sudo apt install -y python3-pip lxd

echo "Setting the default locale. this is useful in case of a new machine"

export LC_ALL="en_US.UTF-8"
export LC_CTYPE="en_US.UTF-8"
sudo dpkg-reconfigure -f noninteractive locales

echo "Executing 'lxd init'. Here are the answers to the questions.


Do you want to configure a new storage pool (yes/no) [default=yes]?
Name of the storage backend to use (dir or zfs) [default=dir]:
Would you like LXD to be available over the network (yes/no) [default=no]? yes
Address to bind LXD to (not including port) [default=all]:
Port to bind LXD to [default=8443]:
Trust password for new clients: openbatontotalsecret
Again: openbatontotalsecret
Do you want to configure the LXD bridge (yes/no) [default=yes]?
   Do you want to setup an IPv4 subnet? Yes
      Default values apply for next questions
   Do you want to setup an IPv6 subnet? No



   "

sudo lxd init
# official documentation says:
#cat <<EOF | lxd init --preseed
#config:
#  core.https_address: [::]:8443
#  core.trust_password: openbatontotalsecret
#networks:
#- name: lxdbr0
#  type: bridge
#  config:
#    ipv4.address: auto
#    ipv6.address: none
#EOF
# but does not work, thus the configuration will be prompted

sudo pip3 install image-generator

wget https://raw.githubusercontent.com/corenetdynamics/image-generator/master/etc/image.yaml

echo -n "Insert chosen LXD Trust Password":
read -s password

sed -i "s/openbatontotalsecret/$password/g" image.yaml

echo "Copy ubuntu image locally"
lxc image copy ubuntu:16.04 local:

echo "Finding fingerprint"
fingerprint=$(lxc image list | grep "ubuntu 16.04 LTS amd64 (release)"| awk '{split($0,a,"|"); print a[3]}' | xargs)
echo "Found fingerprint $fingerprint"

sed -i "s/5f364e2e3f46/$fingerprint/g" image.yaml

sudo mkdir /etc/image-generator

sudo wget https://github.com/corenetdynamics/image-generator/raw/master/files.tar -O /etc/image-generator/files.tar

sudo image-generator -f image.yaml # --debug -dry