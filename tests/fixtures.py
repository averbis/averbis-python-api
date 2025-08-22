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
COLLECTION_NAME = "my-collection"

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


@pytest.fixture()
def requests_mock_id6_7(requests_mock):
    requests_mock.get(
        f"{URL_BASE_ID + '/rest/v1'}/buildInfo",
        headers={"Content-Type": "application/json"},
        json={"payload": {"specVersion": "6.7.0", "buildNumber": ""}, "errorMessages": []},
    )


@pytest.fixture()
def requests_mock_id6_11(requests_mock):
    requests_mock.get(
        f"{URL_BASE_ID + '/rest/v1'}/buildInfo",
        headers={"Content-Type": "application/json"},
        json={"payload": {"specVersion": "6.11.0", "buildNumber": ""}, "errorMessages": []}
    )

@pytest.fixture()
def requests_mock_platform_6_48(requests_mock):
    requests_mock.get(
        f"{URL_BASE_ID + '/rest/v1'}/buildInfo",
        headers={"Content-Type": "application/json"},
        json={"payload": {"specVersion": "6.17.0", "buildNumber": "", "platformVersion": "6.48.0"}, "errorMessages": []},
    )

@pytest.fixture()
def requests_mock_platform_6_50(requests_mock):
    requests_mock.get(
        f"{URL_BASE_ID + '/rest/v1'}/buildInfo",
        headers={"Content-Type": "application/json"},
        json={"payload": {"specVersion": "6.17.0", "buildNumber": "", "platformVersion": "6.50.0"}, "errorMessages": []},
    )


@pytest.fixture()
def requests_mock_platform_7(requests_mock):
    requests_mock.get(
        f"{URL_BASE_ID + '/rest/v1'}/buildInfo",
        headers={"Content-Type": "application/json"},
        json={"payload": {"specVersion": "7.0.0", "buildNumber": "", "platformVersion": "8.4.0"}, "errorMessages": []},
    )


@pytest.fixture()
def requests_mock_platform_8_17(requests_mock):
    requests_mock.get(
        f"{URL_BASE_ID + '/rest/v1'}/buildInfo",
        headers={"Content-Type": "application/json"},
        json={"payload": {"specVersion": "7.13.0", "buildNumber": "", "platformVersion": "8.17.0"}, "errorMessages": []},
    )

@pytest.fixture()
def requests_mock_platform_9(requests_mock):
    requests_mock.get(
        f"{URL_BASE_ID + '/rest/v1'}/buildInfo",
        headers={"Content-Type": "application/json"},
        json={"payload": {"specVersion": "8.0.0", "buildNumber": "", "platformVersion": "9.0.1"}, "errorMessages": []},
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


# Tests that should work in version 6.7
@pytest.fixture()
def client_version_6_7(requests_mock_id6_7):
    return Client(URL_BASE_ID, api_token=TEST_API_TOKEN)


# Tests that should work in version 6.11
@pytest.fixture()
def client_version_6_11(requests_mock_id6_11):
    return Client(URL_BASE_ID, api_token=TEST_API_TOKEN)


# Test that should work with product version 6.17 and platform version 6.48
@pytest.fixture()
def client_version_6_17_0_platform_6_48_0(requests_mock_platform_6_48):
    return Client(URL_BASE_ID, api_token=TEST_API_TOKEN)


# Test that should work with product version 6.17 and platform version 6.50
@pytest.fixture()
def client_version_6_17_platform_6_50(requests_mock_platform_6_50):
    return Client(URL_BASE_ID, api_token=TEST_API_TOKEN)


@pytest.fixture()
def client_version_7(requests_mock_platform_7):
    return Client(URL_BASE_ID, api_token=TEST_API_TOKEN)


@pytest.fixture()
def client_version_7_3_platform_8_17(requests_mock_platform_8_17):
    return Client(URL_BASE_ID, api_token=TEST_API_TOKEN)

@pytest.fixture()
def client_version_8(requests_mock_platform_9):
    return Client(URL_BASE_ID, api_token=TEST_API_TOKEN)
