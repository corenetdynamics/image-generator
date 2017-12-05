# Image-Generator

A python based generator for lxc images.

It will read a configuration from a yaml file, starts a container accordingly,
copies and runs specific scripts and in the end creates a lxc image.

## Prerequisites


```sh
sudo apt update && sudo apt install -y python3-pip lxd
```

After the installation you will need to configure your lxd environment.
Depending on your desired image and scripts the container may need internet connectivity,
so make sure you activate NAT connectivity for your containers:

```sh
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
```


## Install the image generator tool

Install via :

```sh
pip3 install image-generator
```

## How to use

It is possible to run it in two way. `single action` or with `config file`. The config file is a yaml file containing on the root a list of action to be executed in order with some paramters.

Each `action` has specific parameters that are listed in the following section

### Configure

You have at least one lxc image already downloaded which you can find in your local lxc image store

```sh
lxc image list
```

If not, you can import an ubuntu image on the local image repo with the following command:

```sh
lxc image copy ubuntu:16.04 local:
```

And take note of the fingerprint you need for the next steps.


The config file should look like:

```yaml
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
  destination: < Path and Name of the image you are saving >                # default: "gen-image"
  alias: <additional alias to give to the created image>                    # default: "Published by image-generator"

# if the destination does not yet contain the ending tar.gz it will be added automatically

clean:
  container: < remove the container used for creating the lxc image>                        # default: True 
  image-store: < remove the image created from the container from your local image store>   # default: True

# You can (re)import the images anytime by lxc image import < Your path to the desired image.tar.gz > --alias < Your Alias here >
```

### Run

Check the help

```sh
image-generator --help
usage: image-generator [-h] [-f FILE] [-d] [-action ACTION] [-params PARAMS]
                       [-dry]

optional arguments:
  -h, --help            show this help message and exit
  -f FILE, --file FILE  the file scenario with the action to execute
  -d, --debug           show debug prints
  -action ACTION        The action to execute
  -params PARAMS        The parameters to the action
  -dry                  Run dryrun
```

and then run it

```sh
image-generator -f <PATH-TO-THE-CONFIGURATION-FILE>
```

## Uninstall

Uninstall via :

```sh
pip3 uninstall image-generator
```