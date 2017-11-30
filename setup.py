import os

from setuptools import setup, find_packages


def read(fname):
    readme_file_path = os.path.join(os.path.dirname(__file__), fname)

    if os.path.exists(readme_file_path) and os.path.isfile(readme_file_path):
        readme_file = open(readme_file_path)
        return readme_file.read()
    else:
        return "The Image Generator for LXD"


packages = find_packages()

setup(
    name="image-generator",
    version="1.0.0b1",
    author="Open Baton Dev",
    author_email="dev@openbaton.org",
    description="The Image Generator",
    license="Apache 2",
    keywords="python vnfm nfvo lxc open baton openbaton sdk lxd",
    url="http://openbaton.org/",
    packages=packages,
    scripts=["image-generator"],
    install_requires=[
        'pylxd',
        'pyopenssl',
        'pyyaml',
        'progress',
    ],
    long_description=read('README.rst'),
    classifiers=[
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3.5",
        "License :: OSI Approved :: Apache Software License",
    ]
)
