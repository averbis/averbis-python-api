#
# Copyright (c) 2021 Averbis GmbH.
#
# This file is part of Averbis Python API.
# See https://www.averbis.com for further info.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
#

# Note: To use the "upload" functionality of this file, you must:
#   $ pip install twine

import io
import os
import sys
from shutil import rmtree

from setuptools import setup, Command, find_packages

# Package meta-data.
NAME = "averbis-python-api"
DESCRIPTION = "Averbis REST API client for Python."
AUTHOR = "Averbis GmbH"
REQUIRES_PYTHON = ">=3.6.0"

install_requires = [
    "requests",
    "types-requests",
    "dkpro-cassis>=0.6.1"
]

test_dependencies = [
    "pytest>=5.2.1",
    "pytest-lazy-fixture",
    "codecov",
    "pytest-cov",
    "requests-mock",
    "mypy",
    "licenseheaders"
]

dev_dependencies = [
    "black",
    "twine",
    "pygments",
    "licenseheaders"
]

doc_dependencies = [
    "sphinx",
    "sphinx-autodoc-typehints",
    "sphinx-rtd-theme"
]

extras = {
    "test": test_dependencies,
    "dev": dev_dependencies,
    "doc": doc_dependencies
}

# The rest you shouldn"t have to touch too much :)
# ------------------------------------------------
# Except, perhaps the License and Trove Classifiers!
# If you do change the License, remember to change the Trove Classifier for that!

here = os.path.abspath(os.path.dirname(__file__))

# Import the README and use it as the long-description.
# Note: this will only work if "README.rst" is present in your MANIFEST.in file!
try:
    with io.open(os.path.join(here, "README.rst"), encoding="utf-8") as f:
        long_description = "\n" + f.read()
except FileNotFoundError:
    long_description = DESCRIPTION

# Load the package"s __version__.py module as a dictionary.
about: dict = {}
with open(os.path.join(here, "averbis", "__version__.py")) as f:
    exec(f.read(), about)


# Where the magic happens:
setup(
    name=NAME,
    version=about["__version__"],
    description=DESCRIPTION,
    long_description=long_description,
    long_description_content_type="text/x-rst",
    author=AUTHOR,
    #    author_email=EMAIL,
    python_requires=REQUIRES_PYTHON,

    project_urls={
        "Bug Tracker": "https://github.com/averbis/averbis-python-api/issues",
        "Source Code": "https://github.com/averbis/averbis-python-api",
    },

    packages=find_packages(exclude="tests"),

    install_requires=install_requires,
    test_suite="tests",

    tests_require=test_dependencies,
    extras_require=extras,

    include_package_data=True,
    license="Apache License, Version 2.0. Copyright Averbis GmbH",
    classifiers=[
        # Trove classifiers
        # Full list: https://pypi.python.org/pypi?%3Aaction=list_classifiers
        "Development Status :: 4 - Beta",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "License :: OSI Approved :: Apache Software License"
    ],
)
