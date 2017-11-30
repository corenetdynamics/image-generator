import argparse
import base64
import logging
import os
import time

import pylxd
import yaml

import openbaton.utils as utils

logger = logging.getLogger("image-generator")

from pylxd import Client as LxdClient

ALLOWED_ACTIONS = {
    "connect": ["url", "trust-password"],
    "create-container": ["container-name", "container-image-fingerprint"],
    "copy-files": ["file-tarball", "file-dest"],
    "execute-script": ["script"],
    "create-image": ["destination"],
    "clean": ["tmp-files", "container", "image-store"]
}

config = None


def check_config(config: dict) -> (bool, str):
    for k in config.keys():
        if k not in ALLOWED_ACTIONS.keys():
            return False, "action %s is not in allowed actions, please choose between %s" % (k, ALLOWED_ACTIONS.keys())
        for v in config.get(k).keys():
            if v not in ALLOWED_ACTIONS.get(k):
                return False, "field %s is not in allowed field of this action, please choose between %s" % (
                    v, ALLOWED_ACTIONS.get(k))
    return True, None


def authenticate(auth_endpoint: str, trust_password: str) -> LxdClient:
    _, _, cert_path, key_path = utils.generate_certificates()
    # auth_endpoint = config.get('connect').get('url')
    client = LxdClient(endpoint=auth_endpoint,
                       cert=(cert_path, key_path),
                       verify=False,
                       timeout=5)
    try:
        client.authenticate(trust_password)
    except pylxd.exceptions.ClientConnectionFailed:
        logger.error("Error trying to connect to LXD")
        exit(3)
    if not client.trusted:
        logger.error("Problem connecting... you are not trusted!")
    return client


def main():
    created_fingeprint = None
    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--file", help="the file scenario with the action to execute")
    parser.add_argument("-d", "--debug", help="show debug prints", action="store_true")

    parser.add_argument("-action", help="The action to execute")
    parser.add_argument("-params", help="The parameters to the action")

    parser.add_argument("-dry", help="Run dryrun", action="store_true")

    args = parser.parse_args()
    print()
    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.WARNING)

    process_steps = {}
    if args.file:
        with open(args.file, "r") as f:
            process_steps = yaml.load(f.read())

    if process_steps:
        ok, msg = check_config(process_steps)
        if not ok:
            logger.error("%s" % msg)
            exit(1)
        logger.debug("Actions are %s" % process_steps.keys())
    else:
        if not args.action:
            logger.error("Need at least one action")
            exit(2)
        logger.debug("action: %s" % args.action)
        logger.debug("params: %s" % args.params)
        logger.error("Actions are not yet supported...sorry")
        exit(2)

    dryrun = args.dry
    # Authenticate so we are able to use the pylxd libraries
    client = authenticate(process_steps.get('connect').get('url'), process_steps.get('connect').get('trust-password'))
    # Read the desired configuration
    container_name = process_steps.get('create-container').get('container-name')
    # Check for running containers with the same name and eliminate them
    for container in client.containers.all():
        if container.name == container_name:
            logger.debug("Found the container, will delete it and create a new one")
            if not str(container.status) == "Stopped":
                container.stop(wait=True)
            container.delete(wait=True)
    logger.debug("Checking for images")
    container_image = process_steps.get('create-container').get('container-image-fingerprint')
    for image in client.images.all():
        if image.fingerprint.startswith(container_image):
            container_config = {"name": container_name, "source": {"type": "image", "fingerprint": container_image}}
            container = client.containers.create(container_config, wait=True)
            container.start(wait=True)
            # Wait for the network to be up correctly
            time.sleep(4)
            # Check the config for the desired values
            local_tarball = process_steps.get("copy-files").get("file-tarball")
            dest = process_steps.get("copy-files").get("file-dest")
            if os.path.exists(local_tarball):
                # create a temporary file in which we will pass the base64 encoded file-tarball
                tmp_file = "/root/tarball-base64-encoded"
                with open(local_tarball, "rb") as file:
                    base64_data = base64.b64encode(file.read())
                    container.files.put(tmp_file, base64_data)
                    # Be sure the base64 encoded data has been saved
                    file_wait_loop = "until [ -f " + tmp_file + " ]; do sleep 2s; done; "
                    # Dont't forget to decode the base64 file
                    decode = "sleep 4s; cat " + tmp_file + " | base64 --decode > " + dest + "; "
                    # Then we can also unpack the file-tarball
                    unpack = "tar -xvf " + dest + "; "
                    # And execute the desired script
                    install = "./" + process_steps.get('execute-script').get('script')
                    if not dryrun:
                        container.execute(['sh', '-c', file_wait_loop + decode + unpack + install])
                    if process_steps.get('clean').get('tmp-files'):
                        logger.debug("Deleting temporary files from the running container")
                        container.execute(['sh', '-c', "rm " + tmp_file + "; rm " + dest])
                    # Stop the container when finishing the execution of scripts
                    logger.debug("Stopping container in order to create the image")
                    container.stop(wait=True)
                    # Create an image from our container
                    logger.debug("Starting to create the image, this can take a few minutes")
                    created_image = container.publish(wait=True)
                    time.sleep(2)
                    created_image.add_alias(container_name, "Published by image-generator")
                    created_fingeprint = created_image.fingerprint
                    # Now we should have an image of our container in our local image store
                    logger.debug(
                        "Published the container to the local image store as image with the fingerprint : %s" % created_fingeprint)
                    # Check if we want to delete the container
                    if process_steps.get('clean').get('container'):
                        logger.debug("Deleting container as it is not needed anymore")
                        container.delete()
                    break
                    # Thus we can also leave the whole loops..
            else:
                logger.error("Did not found file-tarball : " + local_tarball)
                exit(1)

    if not created_fingeprint:
        logger.error("Base Image with fingerprint starting with %s was not found!")
        exit(3)

    # In the end again check for all images
    for image in client.images.all():
        # In detail for the one we just published
        if image.fingerprint.startswith(created_fingeprint):
            logger.debug("Found the published image.. exporting")
            # And export the image accordingly
            filename = process_steps.get('create-image').get('destination')
            # Check for the correct file ending
            if not filename.endswith('tar.gz'):
                filename = filename + ".tar.gz"
            # Check if the file already exists and delete if necessary
            if os.path.exists(filename):
                os.remove(filename)
            with open(filename, "wb") as image_file:
                logger.debug("Exporting image to: %s" % filename)
                image_file.write(image.export().read())

            if dryrun:
                logger.debug("Removing exported image: %s" % filename)
                os.remove(filename)

            # Workarround for getting it working locally..
            # subprocess.call(['lxc','image','export',created_fingeprint,config.get('create-image').get('destination')])

            # Check if we want to delete the image from the image-store after exporting
            if process_steps.get('clean').get('image-store'):
                logger.debug("Deleting image with fingerprint %s" % created_fingeprint)
                image.delete()
            # Break as we have already found the correct image and do not need the loop anymore
            break
