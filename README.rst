Image-Generator
===============

A python based generator for lxc images.

It will read a configuration from a yaml file, starts a container
accordingly, copies and runs specific scripts and in the end creates a
lxc image.

The following video showcases step by step the instructions detailed on
this README:

|asciicast|

Auto install
------------

There are two scripts for installation and execution.

-  `install.sh <https://github.com/corenetdynamics/image-generator/raw/master/install.sh>`__
-  `run.sh <https://github.com/corenetdynamics/image-generator/raw/master/run.sh>`__

The first script will run the steps described in the ``Manual install``
section. The second one will execute the ``Run`` section steps.

Thus, in order to install and run the image-generator in an automated
way, you can run:

.. code:: bash

    wget https://github.com/corenetdynamics/image-generator/raw/master/install.sh
    wget https://github.com/corenetdynamics/image-generator/raw/master/run.sh

    # install image generator and follow the instructions
    ./install.sh

    # Run it: "Usage: run.sh [-f <yaml-config-file>] [-l <git-link> -s <script-name>] [-d]". For default values just run it as follows
    ./run.sh 

Manual install
--------------

Prerequisites
^^^^^^^^^^^^^

Configure locales
'''''''''''''''''

.. code:: bash

    export LC_ALL="en_US.UTF-8"
    export LC_CTYPE="en_US.UTF-8"
    sudo dpkg-reconfigure -f noninteractive locales

Install pip and lxd
'''''''''''''''''''

.. code:: sh

    sudo apt update && sudo apt install -y python3-pip lxd

Configure lxd
'''''''''''''

After the installation you will need to configure your lxd environment.
Depending on your desired image and scripts the container may need
internet connectivity, so make sure you activate NAT connectivity for
your containers:

.. code:: sh

    sudo lxd init

    Name of the storage backend to use (dir or zfs) [default=dir]:
    Would you like LXD to be available over the network (yes/no) [default=no]? yes
    Address to bind LXD to (not including port) [default=all]:
    Port to bind LXD to [default=8443]:
    Trust password for new clients:
    Again:
    Do you want to configure the LXD bridge (yes/no) [default=yes]?
       Do you want to setup an IPv4 subnet? Yes
          Default values apply for next questions
       Do you want to setup an IPv6 subnet? No

Install the image generator tool
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Install via :

.. code:: bash

    sudo pip3 install image-generator

Configure
^^^^^^^^^

It is possible to run the ``image-generator`` with a config file. The
config file is a yaml file containing on the root a list of action to be
executed in order with some paramters. Each ``action`` has specific
parameters. You have at least one lxc image already downloaded which you
can find in your local lxc image store

.. code:: sh

    lxc image list

If not, you can import an ubuntu image on the local image repo with the
following command:

.. code:: sh

    lxc image copy ubuntu:16.04 local:

And take note of the fingerprint you need for the next steps.

The config file should look like:

.. code:: yaml

    connect:
      url:                        < The URL with port where to reach lxd engine >               # Mandatory
      trust-password:             < The trust password you have set for the lxd environment >                    # Mandatory

    create-container:
      container-name:               < The name of the container which will be created >                                 # default: "image-generator"
      container-image-fingerprint:  < The fingeprint of the image which will be used as base image for the container >  # Mandatory; you do not need the complete image fingerprint, the one shown by lxc image list is enough

    copy-files:
      file-tarball: < Path to the tar archive containing all scripts you want to push on the image >  # default: "./etc/files.tar"
      file-dest:  < Path where to copy the content of the tar archive on the container >              # default /root/files.tar

    execute-script:
      script: < Which script to be executed >                                                       # Mandatory
      clean-tmp-files: < remove the temporary files used for copying the tarball on the container>  # default: False
      # lxc always assumes you are in /root, thus take care if you use relative paths to the scripts here

    create-image:
      destination: < Path of the folder where the image will be saved >         # default: "/tmp"
      alias: <additional alias to give to the created image>                    # default: "Published by image-generator"
      name: <name of the result image>                                          # generated-image
    # if the destination does not yet contain the ending tar.gz it will be added automatically

    clean:
      container: < remove the container used for creating the lxc image>                        # default: True 
      image-store: < remove the image created from the container from your local image store>   # default: True

    # You can (re)import the images anytime by lxc image import < Your path to the desired image.tar.gz > --alias < Your Alias here >

For default values you can run:

.. code:: bash

    # getting default yaml file
    wget https://raw.githubusercontent.com/corenetdynamics/image-generator/master/etc/image.yaml

    # Update password: $password is the lxd trust password chosen while configuring it
    sed -i "s/openbatontotalsecret/$password/g" image.yaml

    # Update the fingerprint in the yaml file
    fingerprint=$(lxc image list | grep "ubuntu 16.04 LTS amd64 (release)"| awk '{split($0,a,"|"); print a[3]}' | xargs)
    sed -i "s/5f364e2e3f46/$fingerprint/g" image.yaml

    # place the tar file containing the script to be executed in the default location
    sudo mkdir /etc/image-generator
    sudo wget https://github.com/corenetdynamics/image-generator/raw/master/files.tar -O /etc/image-generator/files.tar

Run
---

Check the help

.. code:: bash

    sudo image-generator --help
    usage: image-generator [-h] [-f FILE] [-d] [-action ACTION] [-params PARAMS]
                           [-dry]

    optional arguments:
      -h, --help            show this help message and exit
      -f FILE, --file FILE  the file scenario with the action to execute
      -d, --debug           show debug prints
      -action ACTION        The action to execute
      -params PARAMS        The parameters to the action
      -dry                  Run dryrun

and then run it **with sudo**:

.. code:: bash

    sudo image-generator -f image.yaml

sudo rights are needed only because it is required by the process of extracting the image downloaded from lxd.
                                                                                                              

Test it
~~~~~~~

for testing purposes, it is possible to do a dry run by running:

.. code:: bash

    sudo image-generator -f image.yaml -dry --debug

it will execute every step but the installation script and finally will
also delete the downloaded image.

Uninstall
---------

Uninstall via :

.. code:: bash

    sudo pip3 uninstall image-generator

.. |asciicast| image:: https://asciinema.org/a/153313.png
   :target: https://asciinema.org/a/153313
