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
import os

import pytest

from averbis import Client

URL_BASE_ID = "https://localhost:8080/information-discovery"
URL_BASE_HD = "https://localhost:8080/health-discovery"
API_BASE = URL_BASE_ID + "/rest/v1"
API_EXPERIMENTAL = URL_BASE_ID + "/rest/experimental"
TEST_DIRECTORY = os.path.dirname(__file__)
TEST_API_TOKEN = "I-am-a-dummy-API-token"
PROJECT_NAME = "test-project"

## Mock different platforms. The difference between the platforms is in the URL and in the specVersion number.


@pytest.fixture()
def requests_mock_hd5(requests_mock):
    requests_mock.get(
        f"{URL_BASE_HD + '/rest/v1'}/buildInfo",
        headers={"Content-Type": "application/json"},
        json={"payload": {"specVersion": "5.33.0", "buildNumber": ""}, "errorMessages": []},
    )


@pytest.fixture()
def requests_mock_hd6(requests_mock):
    requests_mock.get(
        f"{URL_BASE_HD + '/rest/v1'}/buildInfo",
        headers={"Content-Type": "application/json"},
        json={"payload": {"specVersion": "6.0.0", "buildNumber": ""}, "errorMessages": []},
    )


@pytest.fixture()
def requests_mock_id5(requests_mock):
    requests_mock.get(
        f"{URL_BASE_ID + '/rest/v1'}/buildInfo",
        headers={"Content-Type": "application/json"},
        json={"payload": {"specVersion": "5.33.0", "buildNumber": ""}, "errorMessages": []},
    )


@pytest.fixture()
def requests_mock_id6(requests_mock):
    requests_mock.get(
        f"{URL_BASE_ID + '/rest/v1'}/buildInfo",
        headers={"Content-Type": "application/json"},
        json={"payload": {"specVersion": "6.0.0", "buildNumber": ""}, "errorMessages": []},
    )


## Different clients based on the above platforms

# Tests that should work for all platform versions
@pytest.fixture(params=["5.33.0", "6.0.0"])
def client(request, requests_mock):
    requests_mock.get(
        f"{API_BASE}/buildInfo",
        headers={"Content-Type": "application/json"},
        json={"payload": {"specVersion": request.param, "buildNumber": ""}, "errorMessages": []},
    )
    return Client(URL_BASE_ID, api_token=TEST_API_TOKEN)


# Tests that should work in platform version 5
@pytest.fixture
def client_version_5(requests_mock_id5):
    return Client(URL_BASE_ID, api_token=TEST_API_TOKEN)


# Tests that should work in platform version 6
@pytest.fixture()
def client_version_6(requests_mock_id6):
    return Client(URL_BASE_ID, api_token=TEST_API_TOKEN)
