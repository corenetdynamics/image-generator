import argparse
import base64
import logging
import os
import threading
import time
import traceback

import urllib3
import yaml
from progress.spinner import Spinner

import openbaton.utils as utils
from openbaton.errors import MethodNotFound, ImageCreatedNotFound, ExecutionError, _BaseException, ParameterError

logger = logging.getLogger("img.gen.main")
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

spin = False


def start_spin(msg: str):
    global spin
    spinner = Spinner("%s " % msg)
    spin = True
    while spin:
        spinner.next()
        time.sleep(0.1)
    spinner.finish()
    return


def stop_spin(msg: str):
    global spin
    spin = False
    print("\n%s" % msg)
    return


class ImageGenerator(object):
    def __init__(self, lgr, params, process_steps: dict):
        self.logger = lgr
        self.params = params
        self.process_steps = process_steps
        self.spin = False

    def do_connect(self, own_config: dict, **kwargs) -> dict:
        if kwargs:
            raise ExecutionError("Connect should be run first, without params!")
        # Authenticate so we are able to use the pylxd libraries
        url = own_config.get('url')
        if not url:
            logger.error("connect.url property missing!")
            raise ParameterError("connect.url property missing!")
        self.logger.debug("Authenticating to: %s" % url)
        trust_password = own_config.get('trust-password')
        if not trust_password:
            logger.error("connect.trust_password property missing!")
            raise ParameterError("connect.trust_password property missing!")
        client = utils.authenticate(url,
                                    trust_password)
        kwargs.update({
            'client': client
        })
        return kwargs

    def do_create_container(self, own_config: dict, **kwargs):
        client = kwargs.get('client')
        # Read the desired configuration
        container_name = own_config.get('container-name', "image-generator")
        # Check for running containers with the same name and eliminate them
        for container in client.containers.all():
            if container.name == container_name:
                self.logger.debug("Found the container, will delete it and create a new one")
                if not str(container.status) == "Stopped":
                    container.stop(wait=True)
                container.delete(wait=True)
        self.logger.debug("Checking for images")
        container_image = own_config.get('container-image-fingerprint')
        if not container_image:
            logger.error("create-container.container_image is mandatory!")
            raise ParameterError("create-container.container_image is mandatory!")
        created_fingeprint = None
        for image in client.images.all():
            if image.fingerprint.startswith(container_image):
                container_config = {"name": container_name, "source": {"type": "image", "fingerprint": container_image}}
                container = client.containers.create(container_config, wait=True)
                container.start(wait=True)
                # Wait for the network to be up correctly
                # TODO check when ip is ready
                time.sleep(4)
                # Check the config for the desired values
                kwargs.update({
                    'created_fingeprint': created_fingeprint,
                    'container': container,
                    'container_name': container_name,
                })
                return kwargs

        if not created_fingeprint:
            self.logger.error("Base Image with fingerprint starting with %s was not found!")
            exit(3)

    def do_copy_files(self, own_config: dict, **kwargs):
        container = kwargs.get('container')
        local_tarball = own_config.get("file-tarball", "./etc/file.tar")
        dest = own_config.get("file-dest", "/root/files.tar")
        if os.path.exists(local_tarball):
            # create a temporary file in which we will pass the base64 encoded file-tarball
            tmp_file = "/root/tarball-base64-encoded"
            with open(local_tarball, "rb") as file:
                base64_data = base64.b64encode(file.read())
                container.files.put(tmp_file, base64_data)
                # Be sure the base64 encoded data has been saved

                kwargs.update({
                    'tmp_file': tmp_file,
                    'dest': dest,
                })
                return kwargs

                # Thus we can also leave the whole loops..
        else:
            self.logger.error("Did not found file-tarball : " + local_tarball)
            exit(1)

    def do_execute_script(self, own_config: dict, **kwargs):
        container = kwargs.get('container')
        dest = kwargs.get('dest')
        tmp_file = kwargs.get('tmp_file')
        file_wait_loop = "until [ -f " + tmp_file + " ]; do sleep 2s; done; "
        # Dont't forget to decode the base64 file
        decode = "sleep 4s; cat " + tmp_file + " | base64 --decode > " + dest + "; "
        # Then we can also unpack the file-tarball
        unpack = "tar -xvf " + dest + "; "
        # And execute the desired script
        install_script = own_config.get('script')
        if not install_script:
            logger.error("execute-script.script is mandatory!")
            raise ParameterError("execute-script.script is mandatory!")
        install = "./" + install_script

        if not self.params.dry:
            container.execute(['sh', '-c', file_wait_loop + decode + unpack + install])
        if own_config.get('clean-tmp-files', False):
            self.logger.debug("Deleting temporary files from the running container")
            container.execute(['sh', '-c', "rm " + tmp_file + "; rm " + dest])
        # Stop the container when finishing the execution of scripts
        self.logger.debug("Stopping container in order to create the image")
        container.stop(wait=True)
        return kwargs

    def do_create_image(self, own_config: dict, **kwargs):
        container = kwargs.get('container')
        client = kwargs.get('client')
        container_name = kwargs.get('container_name')
        self.logger.debug("Starting to create the image, this can take a few minutes")
        created_image = container.publish(wait=True)
        time.sleep(2)
        created_image.add_alias(container_name, own_config.get("alias", "Published by image-generator"))
        created_fingeprint = created_image.fingerprint
        # Now we should have an image of our container in our local image store
        self.logger.debug(
            "Published the container to the local image store as image with the fingerprint : %s" % created_fingeprint)

        for image in client.images.all():
            # In detail for the one we just published
            if image.fingerprint.startswith(created_fingeprint):
                logger.debug("Found the published image.. exporting")
                # And export the image accordingly
                filename = own_config.get('destination', "gen-image")
                # Check for the correct file ending
                if not filename.endswith('tar.gz'):
                    filename = filename + ".tar.gz"
                # Check if the file already exists and delete if necessary
                if os.path.exists(filename):
                    os.remove(filename)
                with open(filename, "wb") as image_file:
                    logger.debug("Exporting image to: %s" % filename)
                    image_file.write(image.export().read())

                kwargs.update({
                    "filename": filename,
                    "image": image,
                    "created_fingeprint": created_fingeprint,
                })
                return kwargs
        raise ImageCreatedNotFound("Create Image was not found! This should not happen...")

    def do_clean(self, own_config: dict, **kwargs):

        container = kwargs.get('container')
        filename = kwargs.get('filename')
        image = kwargs.get('image')
        created_fingeprint = kwargs.get('created_fingeprint')
        # Check if we want to delete the container
        container_delete = own_config.get('container', True)
        if isinstance(container_delete, str):
            container_delete = container_delete.lower() == 'true'
        if container_delete:
            self.logger.debug("Deleting container as it is not needed anymore")
            container.delete()
        if self.params.dry:
            logger.debug("Removing exported image: %s" % filename)
            os.remove(filename)

        # Workarround for getting it working locally..
        # subprocess.call(['lxc','image','export',created_fingeprint,config.get('create-image').get('destination')])

        # Check if we want to delete the image from the image-store after exporting
        image_store = own_config.get('image-store', True)
        if isinstance(image_store, str):
            image_store = image_store.lower() == 'true'
        if image_store:
            logger.debug("Deleting image with fingerprint %s" % created_fingeprint)
            image.delete()

        return kwargs


def execute_steps(process_steps: dict, params: dict):
    method_params = {}
    for method_name in process_steps.keys():
        mname = "do_%s" % method_name.replace("-", "_")
        img_gen = ImageGenerator(logging.getLogger("img.gen.ImageGen"), params, process_steps)

        try:
            method = getattr(img_gen, mname)
        except AttributeError:
            raise MethodNotFound(
                "Method with name {} not found in Class `{}`. This should not happen, if you allowed action {} please "
                "also implement respective method {}".format(mname, img_gen.__class__.__name__, method_name, mname))
        t = threading.Thread(target=start_spin, args=("Starting %s..." % method_name,))
        t.start()
        method_params.update(method(own_config=process_steps.get(method_name), **method_params))
        stop_spin("Finished %s." % method_name)
        t.join()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--file", help="the file scenario with the action to execute")
    parser.add_argument("-d", "--debug", help="show debug prints", action="store_true")

    parser.add_argument("-action", help="The action to execute", type=str)
    parser.add_argument("-params",
                        help="The parameters to the action, to follow the structure `key=value key1=value1 ...`",
                        nargs='+',
                        type=str)

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
        ok, msg = utils.check_config(process_steps)
        if not ok:
            logger.error("%s" % msg)
            exit(1)
        logger.debug("Actions are %s" % process_steps.keys())
        try:
            execute_steps(process_steps, args)
        except _BaseException as e:
            if args.debug:
                traceback.print_exc()
            logger.error("Error while ruinnig one command: %s" % e.message)

    else:
        logger.error("Sorry executing single action is not yet supported")
        exit(5)
        action = args.action
        if not action:
            logger.error("Need at least one action")
            exit(2)
        logger.debug("action: %s" % action)
        params = args.params
        logger.debug("params: %s" % params)
        dict_params = {}
        for p in params:
            if "=" in p:
                key_value = p.split("=")
                dict_params[key_value[0]] = key_value[1]
            else:
                logger.error("Parameters must follow the structure `key=value key1=value1 ...`")
        process_steps = {
            action: dict_params
        }
        execute_steps(process_steps, args)
