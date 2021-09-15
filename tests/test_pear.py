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
from averbis import Pear
from tests.fixtures import *


@pytest.fixture()
def pear(client) -> Pear:
    project = client.get_project(PROJECT_NAME)
    return Pear(project, "my_pear_component")


def test_get_parameter(pear, requests_mock):
    configuration = {"param0": "value0", "param1": "value1"}
    requests_mock.get(
        f"{API_EXPERIMENTAL}/textanalysis/projects/{PROJECT_NAME}/pearComponents/{pear.identifier}",
        json={
            "payload": configuration,
            "errorMessages": [],
        },
    )
    actual_configuration = pear.get_default_configuration()
    assert configuration["param0"] == actual_configuration["param0"]
    assert configuration["param1"] == actual_configuration["param1"]
