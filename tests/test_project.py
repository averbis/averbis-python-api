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
import logging
import tempfile
from pathlib import Path

from tests.fixtures import *
from tests.utils import *

logging.basicConfig(level=logging.INFO)


def test_that_create_pipeline_accepts_name_override(client_version_5, requests_mock):
    project = client_version_5.get_project(PROJECT_NAME)
    requests_mock.post(
        f"{API_BASE}/textanalysis/projects/{project.name}/pipelines",
        headers={"Content-Type": "application/json"},
        json={"payload": None, "errorMessages": []},
    )
    configuration = {"pipelineName": "discharge", "schemaVersion": "1.3"}
    pipeline = project.create_pipeline(configuration, name="discharge2")

    assert pipeline.name == "discharge2"


def test_that_create_pipeline_schema_1(client_version_5, requests_mock):
    # The pipeline name parameter is "name" in version 5 and "pipelineName" in version 6
    project = client_version_5.get_project(PROJECT_NAME)
    requests_mock.post(
        f"{API_BASE}/textanalysis/projects/{project.name}/pipelines",
        headers={"Content-Type": "application/json"},
        json={"payload": None, "errorMessages": []},
    )
    configuration = {"name": "discharge-new", "schemaVersion": "1.3"}
    pipeline = project.create_pipeline(configuration)

    assert pipeline.name == "discharge-new"


def test_that_create_pipeline_schema_2(client_version_6, requests_mock):
    # The pipeline name parameter is "name" in version 5 and "pipelineName" in version 6
    project = client_version_6.get_project(PROJECT_NAME)
    requests_mock.post(
        f"{API_BASE}/textanalysis/projects/{project.name}/pipelines",
        headers={"Content-Type": "application/json"},
        json={"payload": None, "errorMessages": []},
    )
    configuration = {"pipelineName": "discharge-new", "schemaVersion": "2.0"}
    pipeline = project.create_pipeline(configuration)

    assert pipeline.name == "discharge-new"


def test_that_get_pipeline_returns_same_instance_on_consecutive_calls(client):
    project = client.get_project(PROJECT_NAME)
    pipeline1 = project.get_pipeline("discharge")
    pipeline2 = project.get_pipeline("discharge")

    assert pipeline1 is pipeline2


def test_list_pipelines(client_version_6, requests_mock):
    project = client_version_6.get_project(PROJECT_NAME)
    requests_mock.get(
        f"{API_EXPERIMENTAL}/textanalysis/projects/{project.name}/pipelines",
        headers={"Content-Type": "application/json"},
        json={
            "payload": [
                {
                    "id": 1,
                    "identifier": "dummy-id1",
                    "name": "Pipeline 1",
                    "description": "",
                    "pipelineState": "STOPPED",
                    "pipelineStateMessage": None,
                    "preconfigured": False,
                },
                {
                    "id": 2,
                    "identifier": "dummy-id2",
                    "name": "Pipeline 2",
                    "description": "",
                    "pipelineState": "STOPPED",
                    "pipelineStateMessage": None,
                    "preconfigured": False,
                },
            ],
            "errorMessages": [],
        },
    )
    pipelines = project.list_pipelines()

    assert pipelines[0].name == "Pipeline 1"
    assert pipelines[0].project == project
    assert pipelines[1].name == "Pipeline 2"
    assert pipelines[1].project == project


def test_exists_pipeline(client_version_6, requests_mock):
    project = client_version_6.get_project(PROJECT_NAME)
    requests_mock.get(
        f"{API_EXPERIMENTAL}/textanalysis/projects/{project.name}/pipelines",
        headers={"Content-Type": "application/json"},
        json={
            "payload": [
                {
                    "id": 1,
                    "identifier": "dummy-id1",
                    "name": "Pipeline 1",
                    "description": "",
                    "pipelineState": "STOPPED",
                    "pipelineStateMessage": None,
                    "preconfigured": False,
                }
            ],
            "errorMessages": [],
        },
    )

    assert project.exists_pipeline("Pipeline 1") is True
    assert project.exists_pipeline("Pipeline 2") is False


def test_list_pear_components(client_version_6, requests_mock):
    project = client_version_6.get_project(PROJECT_NAME)
    expected_pears = ["pear0", "pear1", "pear2"]
    requests_mock.get(
        f"{API_EXPERIMENTAL}/textanalysis/projects/{project.name}/pearComponents",
        headers={"Content-Type": "application/json"},
        json={"payload": expected_pears, "errorMessages": []},
    )
    pear_components = project.list_pears()

    assert pear_components == expected_pears


def test_delete_pear_success(client_version_6, requests_mock):
    project = client_version_6.get_project(PROJECT_NAME)
    pear_identifier = "pear0"
    requests_mock.delete(
        f"{API_EXPERIMENTAL}/textanalysis/projects/{project.name}/pearComponents/{pear_identifier}",
        headers={"Content-Type": "application/json"},
        json={"payload": None, "errorMessages": []},
    )
    project.delete_pear(pear_identifier)


def test_get_processes(client_version_6, requests_mock):
    project = client_version_6.get_project(PROJECT_NAME)
    pipeline_name = "my_pipeline_name"
    state = "IDLE"

    expected_processes_payload = [
        {"processName": "process1", "documentSourceName": "document_source_1"},
        {"processName": "process2", "documentSourceName": "document_source_2"},
        {"processName": "process3", "documentSourceName": "document_source_3"},
    ]

    expected_processes = []
    for i, item in enumerate(expected_processes_payload):
        process_name = item["processName"]
        document_source_name = item["documentSourceName"]
        p = Process(
            project=project,
            name=process_name,
            document_source_name=document_source_name,
            pipeline_name=pipeline_name,
        )
        expected_processes.append(p)

    requests_mock.get(
        f"{API_EXPERIMENTAL}/textanalysis/projects/{project.name}/processes",
        headers={"Content-Type": "application/json"},
        json={"payload": expected_processes_payload, "errorMessages": []},
    )

    for i, item in enumerate(expected_processes_payload):
        process_name = item["processName"]
        document_source_name = item["documentSourceName"]
        payload = {
            "processName": process_name,
            "pipelineName": pipeline_name,
            "documentSourceName": document_source_name,
            "state": state,
            "processedDocuments": i,
        }
        requests_mock.get(
            f"{API_EXPERIMENTAL}/textanalysis/projects/{project.name}/documentSources/{document_source_name}/processes/{process_name}",
            headers={"Content-Type": "application/json"},
            json={"payload": payload, "errorMessages": []},
        )

    actual_processes = project.list_processes()
    assert len(expected_processes_payload) == len(actual_processes)
    [assert_process_equal(a, b) for a, b in zip(expected_processes, actual_processes)]


def test_list_document_collection(client, requests_mock):
    project = client.get_project(PROJECT_NAME)
    requests_mock.get(
        f"{API_BASE}/importer/projects/{project.name}/documentCollections",
        headers={"Content-Type": "application/json"},
        json={
            "payload": [
                {"name": "collection0", "numberOfDocuments": 5},
                {"name": "collection1", "numberOfDocuments": 1},
                {"name": "collection2", "numberOfDocuments": 20},
            ],
            "errorMessages": [],
        },
    )

    collections = project.list_document_collections()

    assert collections[2].name == "collection2"


def test_list_resources(client_version_6, requests_mock):
    project = client_version_6.get_project(PROJECT_NAME)

    expected_resources_list = [
        "test1.txt",
        "test2.txt",
        "test3.txt",
    ]

    requests_mock.get(
        f"{API_EXPERIMENTAL}/textanalysis/projects/{project.name}/resources",
        headers={"Content-Type": "application/json"},
        json={"payload": {"files": expected_resources_list}, "errorMessages": []},
    )

    actual_resources_list = project.list_resources()
    assert actual_resources_list == expected_resources_list


def test_download_resources(client_version_6, requests_mock):
    project = client_version_6.get_project(PROJECT_NAME)

    target_path = Path(TEST_DIRECTORY) / "resources/download/zip_test.zip"
    try:
        os.remove(target_path)
    except OSError:
        pass

    example_text = "some text"
    requests_mock.get(
        f"{API_EXPERIMENTAL}/textanalysis/projects/{project.name}/resources",
        headers={"Content-Type": "application/zip"},
        text=example_text,
    )

    project.download_resources(target_path)

    assert os.path.exists(target_path)
    assert example_text == target_path.read_text()

    os.remove(target_path)


def test_delete_resources(client, requests_mock):
    project = client.get_project(PROJECT_NAME)

    requests_mock.delete(
        f"{API_EXPERIMENTAL}/textanalysis/projects/{project.name}/resources",
        headers={"Content-Type": "application/json"},
        json={"payload": None, "errorMessages": []},
    )

    project.delete_resources()


def test_upload_resources(client_version_6, requests_mock):
    project = client_version_6.get_project(PROJECT_NAME)

    requests_mock.post(
        f"{API_EXPERIMENTAL}/textanalysis/projects/{project.name}/resources",
        headers={"Content-Type": "application/json"},
        status_code=200,
        json={
            "payload": {
                "files": [
                    "text1.txt",
                ]
            },
            "errorMessages": [],
        },
    )
    resources = project.upload_resources(TEST_DIRECTORY + "/resources/zip_test/text1.txt")
    assert len(resources) == 1


def test_delete_pear_with_pear_does_not_exist(client_version_6, requests_mock):
    project = client_version_6.get_project(PROJECT_NAME)
    pear_identifier = "pear0"
    requests_mock.delete(
        f"{API_EXPERIMENTAL}/textanalysis/projects/{project.name}/pearComponents/{pear_identifier}",
        headers={"Content-Type": "application/json"},
        status_code=404,
        json={"payload": None, "errorMessages": ["The requested resource could not be found."]},
    )

    with pytest.raises(Exception) as ex:
        project.delete_pear(pear_identifier)

    expected_error_message = (
        f"404 Server Error: 'None' for url: 'https://localhost:8080/information-discovery/rest/experimental/textanalysis/projects/{PROJECT_NAME}/pearComponents/pear0'.\n"
        "Endpoint error message is: 'The requested resource could not be found.'"
    )
    assert str(ex.value) == expected_error_message


def test_install_pear(client_version_6, requests_mock):
    project = client_version_6.get_project(PROJECT_NAME)
    requests_mock.post(
        f"{API_EXPERIMENTAL}/textanalysis/projects/{project.name}/pearComponents",
        headers={"Content-Type": "application/json"},
        status_code=200,
        json={"payload": ["xyz-pear"], "errorMessages": []},
    )

    with tempfile.NamedTemporaryFile(suffix="xyz.pear") as tf:
        pear_component = project.install_pear(tf.name)
        assert pear_component.identifier == "xyz-pear"


def test_install_pear_with_file_does_not_exist(client_version_6, requests_mock):
    project = client_version_6.get_project(PROJECT_NAME)
    file_or_path = TEST_DIRECTORY + "/resources/pears/nope.pear"
    with pytest.raises(FileNotFoundError) as ex:
        project.install_pear(file_or_path)

    assert file_or_path in str(ex.value)
    assert "No such file or directory" in str(ex.value)


def test_install_pear_with_file_is_not_a_pear(client_version_6, requests_mock):
    project = client_version_6.get_project(PROJECT_NAME)
    with tempfile.NamedTemporaryFile(suffix="xyz.bear") as tf:
        with pytest.raises(Exception) as ex:
            project.install_pear(tf.name)

        assert tf.name in str(ex.value)
        assert "was not of type '.pear'" in str(ex.value)


def test_install_pear_with_pear_already_exists(client_version_6, requests_mock):
    project = client_version_6.get_project(PROJECT_NAME)
    requests_mock.post(
        f"{API_EXPERIMENTAL}/textanalysis/projects/{project.name}/pearComponents",
        headers={"Content-Type": "application/json"},
        status_code=500,
        json={
            "payload": None,
            "errorMessages": [
                "The PEAR component 'xyz.pear' could not be installed since another PEAR component with the ID 'xyz' "
                "already exists. "
            ],
        },
    )
    with tempfile.NamedTemporaryFile(suffix="xyz.pear") as tf:
        with pytest.raises(Exception) as ex:
            project.install_pear(tf.name)

        expected_error_message = (
            f"500 Server Error: 'None' for url: 'https://localhost:8080/information-discovery/rest/experimental/textanalysis/projects/{PROJECT_NAME}/pearComponents'.\n"
            "Endpoint error message is: 'The PEAR component 'xyz.pear' could not be installed since another PEAR component with the ID 'xyz' already exists. '"
        )
        assert expected_error_message == str(ex.value)
