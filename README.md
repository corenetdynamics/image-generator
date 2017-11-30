# Image-Generator

A python based generator for lxc images.

It will read a configuration from a yaml file, starts a container accordingly,
copies and runs specific scripts and in the end creates a lxc image.

## Prerequirements

You have lxc/lxd installed and configured properly, depending on your desired
image and scripts the container may need internet connectivity. You have at least
one lxc image already downloaded which you can find in your local lxc image store

```sh
lxc image list
```

## Install

Install via :

```sh
pip install .
```

## How to use

### Configure

The config file should look like:

```yaml
connect:
  url: < The URL with port where to reach lxc >
  trust-password: < The trust password you have set >

# Both of these values require that you have set the related values in the lxc config
    # lxc config set core.https_address "[::]"
    # lxc config set core.trust_password < Your Password here >

create-container:
  container-name: < The name of the container which will be created >
  container-image-fingerprint: < The fingeprint of the image which will be used as base image for the container >

# You do not need the complete image fingerprint, the one shown by lxc image list is enough

copy-files:
  file-tarball: < Path to the tar archive containing all scripts you want to push on the image >
  file-dest:  < Path where to copy the content of the tar archive on the container >

execute-script:
  script: < Which script to be executed >

# lxc always assumes you are in /root, thus take care if you use relative paths to the scripts here

create-image:
  destination: < Path and Name of the image you are saving >

# if the destination does not yet contain the ending tar.gz it will be added automatically

clean:
  tmp-files: < True or False >
  container: < True or False >
  image-store: < True or False >

# Booleans if you want to
    -   remove the temporary files used for copying the tarball on the container
    -   remove the container used for creating the lxc image
    -   remove the image created from the container from your local image store

# You can (re)import the images anytime by lxc image import < Your path to the desired image.tar.gz > --alias < Your Alias here >

```

### Run

image-generator -f <PATH-TO-THE-CONFIGURATION-FILE>

## Uninstall

Uninstall via :

```sh
pip uninstall image-generator -y
```