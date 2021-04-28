Averbis Python API
==================

.. image:: https://img.shields.io/pypi/v/averbis-python-api.svg
  :alt: PyPI
  :target: https://pypi.org/project/averbis-python-api/

.. image:: https://readthedocs.org/projects/averbis-python-api/badge/?version=latest
  :target: https://averbis-python-api.readthedocs.io/en/latest/?badge=latest
  :alt: Documentation Status

.. image:: https://github.com/averbis/averbis-python-api/workflows/Build/badge.svg?branch=main
  :target: https://github.com/averbis/averbis-python-api/actions?query=workflow%3A%22Build%22
  :alt: Build Status

.. image:: https://codecov.io/gh/averbis/averbis-python-api/branch/main/graph/badge.svg
  :target: https://codecov.io/gh/averbis/averbis-python-api
  :alt: Test Coverage Status

.. image:: https://img.shields.io/pypi/l/averbis-python-api
  :alt: PyPI - License
  :target: https://pypi.org/project/averbis-python-api/
  
.. image:: https://img.shields.io/pypi/pyversions/averbis-python-api.svg
  :alt: PyPI - Python Version
  :target: https://pypi.org/project/averbis-python-api/

.. image:: https://img.shields.io/badge/code%20style-black-000000.svg
  :target: https://github.com/averbis/averbis-python-api
  :alt: Code Style
  
`Averbis <https://averbis.com>`_ is a leading text mining and machine learning company in Healthcare and Life Sciences. We extract information from texts, automate intellectual processes and make meaningful predictions.

The **Averbis Python API** allows convenient access to the REST API of Averbis products. This includes in particular the ability to interact with the text mining pipelines offered by these products, e.g. to use these in data science environments such as Jupyter notebooks or for integration of the Averbis products in other enterprise systems.

Supported products are:

- `Health Discovery <https://averbis.com/health-discovery/>`_

- `Information Discovery <https://averbis.com/information-discovery/>`_

- `Patent Monitor <https://averbis.com/patent-monitor/>`_

Status
------

The Averbis Python API is currently in an open alpha development stage. We try to keep breaking changes minimal but they may happen on the way to the first stable release.

Features
--------

Currently supported features are:

- Managing projects
- Managing pipelines
- Managing terminologies
- Analysing text using a server-side text mining pipeline
- Classifying texts using a server-side classifier

Installation
------------

The library can be installed easily via :code:`pip`

.. code-block:: shell

  pip install averbis-python-api

Documentation
-------------

To get an overview over the methods provided with the client and the corresponding documentation, we refer to our `readthedocs API reference <https://averbis-python-api.readthedocs.io/en/latest/index.html>`_.

Moreover, we will provide a number of example jupyter notebooks that showcase the usage of the client to solve different use cases in an upcoming release.


Usage
-----


Connecting the client to a platform
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code:: python

  from averbis import Client
  # Use existing API Token
  client = Client('http://localhost:8400/health-discovery', api_token='YOUR_API_TOKEN')
  # or generate new API Token based on your credentials (invalidates old API Token)
  client = Client('http://localhost:8400/health-discovery', username = 'YOUR_USERNAME', password = 'YOUR_PASSWORD') 


Connecting to a pipeline and assure that it is started
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code:: python

  pipeline = client.get_project('YOUR_PROJECT_NAME').get_pipeline('YOUR_PIPELINE_NAME')
  pipeline.ensure_started()


Analysing a string
~~~~~~~~~~~~~~~~~~

.. code:: python

  document = 'This is the string we want to analyse.'
  annotations = pipeline.analyse_text(document, language='en')
  for annotation in annotations:
      print(annotation)


Analysing a text file
~~~~~~~~~~~~~~~~~~~~~

.. code:: python

  with open('/path/to/text_file.txt', 'rb') as document:
      annotations = pipeline.analyse_text(document, language='en')
      for annotation in annotations:
          print(annotation)


Restricting returned annotation types
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code:: python

  annotations = pipeline.analyse_text(document, language='en',
      annotation_types='*Diagnosis') # will return only annotations that end with 'Diagnosis'


Connection profiles
~~~~~~~~~~~~~~~~~~~

To avoid storing API keys in the Python scripts or constantly re-generating them, it is
possible to store the keys for commonly used servers in a configuration file. This file
must be called :code:`client-settings.json` and it must be located either in the working directory
of the script or in the user's home folder in :code:`.averbis/client-settings.json`.

Each profile has three settings:

- :code:`url`: the base URL of the server application
- :code:`api-token`: the API token
- :code:`verify-ssl`: the path to a PEM file used to validate the server certificate if SSL is used

Default settings which should be applied to all profiles can be stored in the special profile :code:`*` (star).

.. code:: json

  {
    "profiles": {
      "*": {
        "verify-ssl": "caRoot.pem"
      },
      "localhost-hd": {
        "url": "https://localhost:8080/health-discovery",
        "api-token": "dummy-token"
      },
      "localhost-id": {
        "url": "https://localhost:8080/information-discovery",
        "api-token": "dummy-token",
        "verify-ssl": "id.pem"
      }
    }
  }


Development
------------

To set up a local development environment, check out the repository, set up a virtual environment
and install the required dependencies (if :code:`--no-site-packages` does not work on your system, omit it):

.. code-block:: shell

  virtualenv venv --python=python3 --no-site-packages
  source venv/bin/activate
  pip install -e ".[test, dev, doc]"

To install the latest development version of the library directly from GitHub, you can use the following command:

.. code-block:: shell

  $ pip install --upgrade git+https://github.com/averbis/averbis-python-api.git
