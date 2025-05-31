from setuptools import setup, find_packages
from codecs import open
from os import path


__author__ = "Giulio Rossetti"
__license__ = "GPL-3.0"
__email__ = "giulio.rossetti@gmail.com"


here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(here, "README.md"), encoding="utf-8") as f:
    long_description = f.read()

with open(path.join(here, "requirements.txt"), encoding="utf-8") as f:
    requirements = f.read().splitlines()


setup(
    name="ysights",
    version="0.1.0",
    license="GPL-3.0",
    description="ySights - Extract insights from YSocial simulations",
    url="https://github.com/YSocialTwin/ysights",
    author="Giulio Rossetti",
    author_email="giulio.rossetti@gmail.com",
    classifiers=[
        # How mature is this project? Common values are
        #   3 - Alpha
        #   4 - Beta
        #   5 - Production/Stable
        "Development Status :: 4 - Beta",
        # Indicate who your project is intended for
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Build Tools",
        # Pick your license as you wish (should match "license" above)
        "License :: OSI Approved :: BSD License",
        "Operating System :: POSIX :: Other",
        "Operating System :: MacOS",
        # Specify the Python versions you support here. In particular, ensure
        # that you indicate whether you support Python 2, Python 3 or both.
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
    ],
    keywords="community-discovery node-clustering edge-clustering complex-networks",
    install_requires=requirements,
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(
        exclude=["*.test", "*.test.*", "test.*", "test", "cdlib.test", "cdlib.test.*"]
    ),
)
