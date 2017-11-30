import datetime
import os
import random

from OpenSSL import crypto


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


