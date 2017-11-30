import argparse

import yaml
import openbaton.utils as utils
import os
import base64
import time
import subprocess

from pylxd import Client as LxdClient

ALLOWED_ACTIONS = {
    "connect":          ["url", "trust-password"],
    "create-container": ["container-name","container-image-fingerprint"],
    "copy-files":       ["file-tarball","file-dest"],
    "execute-script":   ["script"],
    "create-image":     ["destination"],
    "clean":            ["tmp-files","container","image-store"]
}

config = None
dryrun=False

def check_config(config: dict) -> (bool, str):
    for k in config.keys():
        if k not in ALLOWED_ACTIONS.keys():
            return False, "action %s is not in allowed actions, please choose between %s" % (k, ALLOWED_ACTIONS.keys())
        for v in config.get(k).keys():
            if v not in ALLOWED_ACTIONS.get(k):
                return False, "field %s is not in allowed field of this action, please choose between %s" % (
                v, ALLOWED_ACTIONS.get(k))
    return True, None


def authenticate(config:dict) -> LxdClient:
    _,_,cert_path, key_path = utils.generate_certificates()
    auth_endpoint=config.get('connect').get('url')
    client = LxdClient(endpoint=auth_endpoint,
                       cert=(cert_path,key_path),
                       verify=False,
                       timeout=5)
    client.authenticate(config.get('connect').get('trust-password'))
    if not client.trusted:
        print("Problem connecting..")
    return client



def main():
    created_fingeprint= None
    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--file", help="the file scenario with the action to execute")
    # parser.add_argument("-u", "--username", help="the openbaton username")
    # parser.add_argument("-p", "--password", help="the openbaton password")
    parser.add_argument("-d", "--debug", help="show debug prints", action="store_true")

    parser.add_argument("-action", help="The action to execute")
    parser.add_argument("-params", help="The parameters to the action")

    args = parser.parse_args()

    if args.file:
        with open(args.file, "r") as f:
            config = yaml.load(f.read())

    if config:
        ok, msg = check_config(config)
        if not ok:
            print("ERROR: %s" % msg)
            exit(1)
        print("Actions are %s" % config.keys())
    else:
        print("action: %s" % args.action)
        print("params: %s" % args.params)

    # Authenticate so we are able to use the pylxd libraries
    client=authenticate(config)
    # Read the desired configuration
    container_name=config.get('create-container').get('container-name')
    # Check for running containers with the same name and eliminate them
    for container in client.containers.all():
        if container.name == container_name:
            print("Found the container, will delete it and create a new one")
            if not str(container.status) == "Stopped" :
                container.stop(wait=True)
            container.delete(wait=True)
    print("Checking for images")
    container_image=config.get('create-container').get('container-image-fingerprint')
    for image in client.images.all():
        if image.fingerprint.startswith(container_image):
            container_config = {"name": container_name, "source": {"type": "image", "fingerprint": container_image}}
            container = client.containers.create(container_config, wait=True)
            container.start(wait=True)
            # Wait for the network to be up correctly
            time.sleep(4)
            # Check the config for the desired values
            local_tarball=config.get("copy-files").get("file-tarball")
            dest=config.get("copy-files").get("file-dest")
            if os.path.exists(local_tarball):
                # create a temporary file in which we will pass the base64 encoded file-tarball
                tmp_file="/root/tarball-base64-encoded"
                with open(local_tarball,"rb") as file:
                    base64_data=base64.b64encode(file.read())
                    container.files.put(tmp_file,base64_data)
                    # Be sure the base64 encoded data has been saved
                    file_wait_loop="until [ -f "+tmp_file+ " ]; do sleep 2s; done; "
                    # Dont't forget to decode the base64 file
                    decode="sleep 4s; cat "+tmp_file+" | base64 --decode > "+dest+"; "
                    # Then we can also unpack the file-tarball
                    unpack="tar -xvf "+dest+"; "
                    # And execute the desired script
                    install="./"+config.get('execute-script').get('script')
                    if not dryrun:
                        container.execute(['sh','-c',file_wait_loop+decode+unpack+install])
                    if config.get('clean').get('tmp-files'):
                        print("Deleting temporary files from the running container")
                        container.execute(['sh','-c',"rm "+tmp_file+"; rm "+dest])
                    # Stop the container when finishing the execution of scripts
                    print("Stopping container in order to create the image")
                    container.stop(wait=True)
                    # Create an image from our container
                    print("Starting to create the image, this can take a few minutes")
                    created_image=container.publish(wait=True)
                    time.sleep(2)
                    created_image.add_alias(container_name,"Published by image-generator")
                    created_fingeprint=created_image.fingerprint
                    # Now we should have an image of our container in our local image store
                    print("Published the container to the local image store as image with the fingerprint : ")
                    print(created_fingeprint)
                    # Check if we want to delete the container
                    if config.get('clean').get('container'):
                        print("Deleting container as it is not needed anymore")
                        container.delete()
                    break
                    # Thus we can also leave the whole loops..
            else :
                print("Did not found file-tarball : ")
                print(local_tarball)
                exit(1)

    # In the end again check for all images
    for image in client.images.all():
        # In detail for the one we just published
        if image.fingerprint.startswith(created_fingeprint):
            print("Found the published image.. exporting")
            # And export the image accordingly
            filename=config.get('create-image').get('destination')
            # Check for the correct file ending
            if not filename.endswith('tar.gz'):
                filename=filename+".tar.gz"
            # Check if the file already exists and delete if necessary
            if os.path.exists(filename):
                os.remove(filename)
            with open(filename, "wb") as image_file:
                image_file.write(image.export().read())

            # Workarround for getting it working locally..
            #subprocess.call(['lxc','image','export',created_fingeprint,config.get('create-image').get('destination')])

            # Check if we want to delete the image from the image-store after exporting
            if config.get('clean').get('image-store'):
                print("Deleting image with fingerprint")
                print(created_fingeprint)
                image.delete()
            # Break as we have already found the correct image and do not need the loop anymore
            break