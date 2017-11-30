import datetime
import logging
import os
import random

import pylxd
from OpenSSL import crypto
from pylxd import Client as LxdClient

logger = logging.getLogger("img.gen.utils")

ALLOWED_ACTIONS = {
    "connect": ["url", "trust-password"],
    "create-container": ["container-name", "container-image-fingerprint"],
    "copy-files": ["file-tarball", "file-dest"],
    "execute-script": ["script", "clean-tmp-files"],
    "create-image": ["destination", "alias"],
    "clean": ["tmp-files", "container", "image-store"]
}


def authenticate(auth_endpoint: str, trust_password: str) -> LxdClient:
    _, _, cert_path, key_path = generate_certificates()
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


def check_config(config: dict) -> (bool, str):
    for k in config.keys():
        if k not in ALLOWED_ACTIONS.keys():
            return False, "action %s is not in allowed actions, please choose between %s" % (k, ALLOWED_ACTIONS.keys())
        for v in config.get(k).keys():
            if v not in ALLOWED_ACTIONS.get(k):
                return False, "field %s is not in allowed field for action '%s', please choose between %s" % (
                    v, k, ALLOWED_ACTIONS.get(k))
    return True, None


def generate_certificates(key_name: str = 'image-generator',
                          cert_location: str = '/etc/image-generator/lxd',
                          common_name: str = 'image-generator-lxd',
                          days: int = 364) -> (bytes, bytes):
    if not os.path.exists(cert_location):
        os.makedirs(cert_location)

    k = crypto.PKey()
    k.generate_key(crypto.TYPE_RSA, 2048)

    cert = crypto.X509()
    cert.get_subject().commonName = common_name
    cert.set_serial_number(random.randint(990000, 999999999999999999999999999))
    cert.gmtime_adj_notBefore(-600)
    cert.gmtime_adj_notAfter(int(datetime.timedelta(days=days).total_seconds()))
    cert.set_issuer(cert.get_subject())
    cert.set_pubkey(k)
    cert.sign(k, 'sha1')

    certificate = crypto.dump_certificate(crypto.FILETYPE_PEM, cert)
    private_key = crypto.dump_privatekey(crypto.FILETYPE_PEM, k)
    key_path = "%s/%s.key" % (cert_location, key_name)
    if not os.path.exists(key_path):
        with open(key_path, 'w') as f:
            f.write(private_key.decode('utf-8'))
    cert_path = "%s/%s.crt" % (cert_location, key_name)
    if not os.path.exists(cert_path):
        with open(cert_path, 'w') as f:
            f.write(certificate.decode('utf-8'))
    return private_key, certificate, cert_path, key_path
