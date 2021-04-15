#
# Copyright (c) 2020 Averbis GmbH.
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
import logging

from tests.fixtures import *

logging.basicConfig(level=logging.INFO)


def test_that_create_pipeline_accepts_name_override(client_version_5, requests_mock):
    project = client_version_5.get_project("LoadTesting")
    requests_mock.post(
        f"{API_BASE}/textanalysis/projects/LoadTesting/pipelines",
        headers={"Content-Type": "application/json"},
        json={"payload": None, "errorMessages": []},
    )
    configuration = {"pipelineName": "discharge", "schemaVersion": "1.3"}
    pipeline = project.create_pipeline(configuration, name="discharge2")

    assert pipeline.name == "discharge2"


def test_that_create_pipeline_schema_1(client_version_5, requests_mock):
    # The pipeline name parameter is "name" in version 5 and "pipelineName" in version 6
    project = client_version_5.get_project("LoadTesting")
    requests_mock.post(
        f"{API_BASE}/textanalysis/projects/LoadTesting/pipelines",
        headers={"Content-Type": "application/json"},
        json={"payload": None, "errorMessages": []},
    )
    configuration = {"name": "discharge-new", "schemaVersion": "1.3"}
    pipeline = project.create_pipeline(configuration)

    assert pipeline.name == "discharge-new"


def test_that_create_pipeline_schema_2(client_version_6, requests_mock):
    # The pipeline name parameter is "name" in version 5 and "pipelineName" in version 6
    project = client_version_6.get_project("LoadTesting")
    requests_mock.post(
        f"{API_BASE}/textanalysis/projects/LoadTesting/pipelines",
        headers={"Content-Type": "application/json"},
        json={"payload": None, "errorMessages": []},
    )
    configuration = {"pipelineName": "discharge-new", "schemaVersion": "2.0"}
    pipeline = project.create_pipeline(configuration)

    assert pipeline.name == "discharge-new"


def test_that_get_pipeline_returns_same_instance_on_consecutive_calls(client):
    project = client.get_project("LoadTesting")
    pipeline1 = project.get_pipeline("discharge")
    pipeline2 = project.get_pipeline("discharge")

    assert pipeline1 is pipeline2


def test_list_pear_components(client_version_6, requests_mock):
    project = client_version_6.get_project("LoadTesting")
    expected_pears = [
        'pear0',
        'pear1',
        'pear2'
    ]
    requests_mock.get(
        f"{API_EXPERIMENTAL}/textanalysis/projects/LoadTesting/pearComponents",
        headers={"Content-Type": "application/json"},
        json={"payload": expected_pears, "errorMessages": []},
    )
    pear_components = project.list_pear_components()

    assert pear_components == expected_pears


def test_delete_pear_component_success(client_version_6, requests_mock):
    project = client_version_6.get_project("LoadTesting")
    pear_identifier = 'pear0'
    requests_mock.delete(
        f"{API_EXPERIMENTAL}/textanalysis/projects/LoadTesting/pearComponents/{pear_identifier}",
        headers={"Content-Type": "application/json"},
        json={"payload": None, "errorMessages": []},
    )
    project.delete_pear_component(pear_identifier)


def test_delete_pear_component_pear_does_not_exist(client_version_6, requests_mock):
    project = client_version_6.get_project("LoadTesting")
    pear_identifier = 'pear0'
    requests_mock.delete(
        f"{API_EXPERIMENTAL}/textanalysis/projects/LoadTesting/pearComponents/{pear_identifier}",
        headers={"Content-Type": "application/json"},
        status_code=404,
        json={
            "payload": None,
            "errorMessages": [
                "The requested resource could not be found."
            ]
        }
    )

    with pytest.raises(Exception) as ex:
        project.delete_pear_component(pear_identifier)

    # the assert needs to be on this level
    expected_error_message = 'Unable to perform request: The requested resource could not be found.'
    assert expected_error_message in str(ex.value)


def test_install_pear_component(client_version_6, requests_mock):
    project = client_version_6.get_project("LoadTesting")
    requests_mock.post(
        f"{API_EXPERIMENTAL}/textanalysis/projects/LoadTesting/pearComponents",
        headers={"Content-Type": "application/json"},
        status_code=200,
        json={"payload": ["xyz-pear"], "errorMessages": []}
    )
    file_path = os.path.join(TEST_DIRECTORY, "resources/pears/xyz.pear")
    pear_component = project.install_pear_component(file_path)
    assert pear_component.identifier == 'xyz-pear'


def test_install_pear_component_file_does_not_exist(client_version_6, requests_mock):
    project = client_version_6.get_project("LoadTesting")
    file_or_path = TEST_DIRECTORY + '/' + "resources/pears/nope.pear"
    with pytest.raises(FileNotFoundError) as ex:
        project.install_pear_component(file_or_path)

    assert file_or_path in str(ex.value)
    assert 'No such file or directory' in str(ex.value)


def test_install_pear_component_file_is_not_a_pear(client_version_6, requests_mock):
    project = client_version_6.get_project("LoadTesting")
    file_or_path = TEST_DIRECTORY + '/' + "resources/pears/xyz.bear"

    with pytest.raises(Exception) as ex:
        project.install_pear_component(file_or_path)

    assert file_or_path in str(ex.value)
    assert "was not of type '.pear'" in str(ex.value)


def test_install_pear_component_already_exists(client_version_6, requests_mock):
    project = client_version_6.get_project("LoadTesting")
    requests_mock.post(
        f"{API_EXPERIMENTAL}/textanalysis/projects/LoadTesting/pearComponents",
        headers={"Content-Type": "application/json"},
        status_code=404,
        json={
            "payload": None,
            "errorMessages": [
                "The PEAR component 'xyz.pear' could not be installed since another PEAR component with the ID 'xyz' "
                "already exists. "
            ]
        }
    )
    file_path = os.path.join(TEST_DIRECTORY, "resources/pears/xyz.pear")

    with pytest.raises(Exception) as ex:
        project.install_pear_component(file_path)

    expected_error_message = "Unable to perform request: The PEAR component 'xyz.pear' could not be installed since " \
                             "another PEAR component with the ID 'xyz' already exists. "
    assert expected_error_message in str(ex.value)
