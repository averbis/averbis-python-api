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

from averbis import Process
from tests.fixtures import *

logging.basicConfig(level=logging.INFO)


def test_that_create_pipeline_accepts_name_override(client_version_5, requests_mock):
    project = client_version_5.get_project("test-project")
    requests_mock.post(
        f"{API_BASE}/textanalysis/projects/test-project/pipelines",
        headers={"Content-Type": "application/json"},
        json={"payload": None, "errorMessages": []},
    )
    configuration = {"pipelineName": "discharge", "schemaVersion": "1.3"}
    pipeline = project.create_pipeline(configuration, name="discharge2")

    assert pipeline.name == "discharge2"


def test_that_create_pipeline_schema_1(client_version_5, requests_mock):
    # The pipeline name parameter is "name" in version 5 and "pipelineName" in version 6
    project = client_version_5.get_project("test-project")
    requests_mock.post(
        f"{API_BASE}/textanalysis/projects/test-project/pipelines",
        headers={"Content-Type": "application/json"},
        json={"payload": None, "errorMessages": []},
    )
    configuration = {"name": "discharge-new", "schemaVersion": "1.3"}
    pipeline = project.create_pipeline(configuration)

    assert pipeline.name == "discharge-new"


def test_that_create_pipeline_schema_2(client_version_6, requests_mock):
    # The pipeline name parameter is "name" in version 5 and "pipelineName" in version 6
    project = client_version_6.get_project("test-project")
    requests_mock.post(
        f"{API_BASE}/textanalysis/projects/test-project/pipelines",
        headers={"Content-Type": "application/json"},
        json={"payload": None, "errorMessages": []},
    )
    configuration = {"pipelineName": "discharge-new", "schemaVersion": "2.0"}
    pipeline = project.create_pipeline(configuration)

    assert pipeline.name == "discharge-new"


def test_that_get_pipeline_returns_same_instance_on_consecutive_calls(client):
    project = client.get_project("test-project")
    pipeline1 = project.get_pipeline("discharge")
    pipeline2 = project.get_pipeline("discharge")

    assert pipeline1 is pipeline2


def test_list_pear_components(client_version_6, requests_mock):
    project = client_version_6.get_project("test-project")
    expected_pears = ["pear0", "pear1", "pear2"]
    requests_mock.get(
        f"{API_EXPERIMENTAL}/textanalysis/projects/test-project/pearComponents",
        headers={"Content-Type": "application/json"},
        json={"payload": expected_pears, "errorMessages": []},
    )
    pear_components = project.list_pears()

    assert pear_components == expected_pears


def test_delete_pear_success(client_version_6, requests_mock):
    project = client_version_6.get_project("test-project")
    pear_identifier = "pear0"
    requests_mock.delete(
        f"{API_EXPERIMENTAL}/textanalysis/projects/test-project/pearComponents/{pear_identifier}",
        headers={"Content-Type": "application/json"},
        json={"payload": None, "errorMessages": []},
    )
    project.delete_pear(pear_identifier)


def test_create_and_run_process(client_version_6, requests_mock):
    project = client_version_6.get_project("test-project")
    process_name = "my_process"
    document_source_name = "my_document_source"
    pipeline_name = "my_pipeline_name"
    state = "IDLE"
    number_of_documents = 12

    requests_mock.post(
        f"{API_EXPERIMENTAL}/textanalysis/projects/test-project/processes",
        headers={"Content-Type": "application/json"},
        json={"payload": None, "errorMessages": []},
    )

    requests_mock.get(
        f"{API_EXPERIMENTAL}/textanalysis/projects/test-project/"
        f"documentSources/{document_source_name}/processes/{process_name}",
        headers={"Content-Type": "application/json"},
        json={
            "payload": {
                "processName": process_name,
                "pipelineName": pipeline_name,
                "documentSourceName": document_source_name,
                "state": state,
                "processedDocuments": number_of_documents,
            },
            "errorMessages": [],
        },
    )

    actual_process = project.create_and_run_process(
        process_name, document_source_name, pipeline_name
    )

    expected_process = Process(project, process_name, document_source_name, pipeline_name)
    assert_process_equal(expected_process, actual_process)


def test_get_process(client_version_6, requests_mock):
    project = client_version_6.get_project("test-project")
    process_name = "my_process"
    document_source_name = "my_document_source"
    pipeline_name = "my_pipeline_name"
    state = "IDLE"
    number_of_documents = 12

    expected_process = Process(project, process_name, document_source_name, pipeline_name)

    payload = {
        "processName": process_name,
        "pipelineName": pipeline_name,
        "documentSourceName": document_source_name,
        "state": state,
        "processedDocuments": number_of_documents,
    }

    requests_mock.get(
        f"{API_EXPERIMENTAL}/textanalysis/projects/test-project/"
        f"documentSources/{document_source_name}/processes/{process_name}",
        headers={"Content-Type": "application/json"},
        json={"payload": payload, "errorMessages": []},
    )
    actual = project.get_process(process_name, document_source_name)
    assert_process_equal(expected_process, actual)


def assert_process_equal(expected_process, actual):
    assert expected_process.name == actual.name
    assert expected_process.project.name == actual.project.name
    assert expected_process.pipeline_name == actual.pipeline_name
    assert expected_process.document_source_name == actual.document_source_name


def test_get_processes(client_version_6, requests_mock):
    project = client_version_6.get_project("test-project")
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
        f"{API_EXPERIMENTAL}/textanalysis/projects/test-project/processes",
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
            f"{API_EXPERIMENTAL}/textanalysis/projects/test-project/"
            f"documentSources/{document_source_name}/processes/{process_name}",
            headers={"Content-Type": "application/json"},
            json={"payload": payload, "errorMessages": []},
        )

    actual_processes = project.list_processes()
    assert len(expected_processes_payload) == len(actual_processes)
    [assert_process_equal(a, b) for a, b in zip(expected_processes, actual_processes)]


def test_delete_pear_with_pear_does_not_exist(client_version_6, requests_mock):
    project = client_version_6.get_project("test-project")
    pear_identifier = "pear0"
    requests_mock.delete(
        f"{API_EXPERIMENTAL}/textanalysis/projects/test-project/pearComponents/{pear_identifier}",
        headers={"Content-Type": "application/json"},
        status_code=404,
        json={"payload": None, "errorMessages": ["The requested resource could not be found."]},
    )

    with pytest.raises(Exception) as ex:
        project.delete_pear(pear_identifier)

    expected_error_message = "Unable to perform request: The requested resource could not be found."
    assert expected_error_message in str(ex.value)


def test_install_pear(client_version_6, requests_mock):
    project = client_version_6.get_project("test-project")
    requests_mock.post(
        f"{API_EXPERIMENTAL}/textanalysis/projects/test-project/pearComponents",
        headers={"Content-Type": "application/json"},
        status_code=200,
        json={"payload": ["xyz-pear"], "errorMessages": []},
    )

    with tempfile.NamedTemporaryFile(suffix="xyz.pear") as tf:
        pear_component = project.install_pear(tf.name)
        assert pear_component.identifier == "xyz-pear"


def test_install_pear_with_file_does_not_exist(client_version_6, requests_mock):
    project = client_version_6.get_project("test-project")
    file_or_path = TEST_DIRECTORY + "/" + "resources/pears/nope.pear"
    with pytest.raises(FileNotFoundError) as ex:
        project.install_pear(file_or_path)

    assert file_or_path in str(ex.value)
    assert "No such file or directory" in str(ex.value)


def test_install_pear_with_file_is_not_a_pear(client_version_6, requests_mock):
    project = client_version_6.get_project("test-project")
    with tempfile.NamedTemporaryFile(suffix="xyz.bear") as tf:
        with pytest.raises(Exception) as ex:
            project.install_pear(tf.name)

        assert tf.name in str(ex.value)
        assert "was not of type '.pear'" in str(ex.value)


def test_install_pear_with_pear_already_exists(client_version_6, requests_mock):
    project = client_version_6.get_project("test-project")
    requests_mock.post(
        f"{API_EXPERIMENTAL}/textanalysis/projects/test-project/pearComponents",
        headers={"Content-Type": "application/json"},
        status_code=404,
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
            "Unable to perform request: The PEAR component 'xyz.pear' could not be installed "
            "since another PEAR component with the ID 'xyz' already exists. "
        )
        assert expected_error_message in str(ex.value)
