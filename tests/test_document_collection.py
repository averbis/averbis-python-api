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
from pathlib import Path

from cassis import Cas, TypeSystem

from averbis import DocumentCollection, Process
from tests.fixtures import *
from tests.utils import *


@pytest.fixture()
def document_collection(client) -> DocumentCollection:
    project = client.get_project(PROJECT_NAME)
    return DocumentCollection(project, "test-collection")


def test_import_plain_text(document_collection, requests_mock):
    requests_mock.post(
        f"{API_BASE}/importer/projects/{PROJECT_NAME}/documentCollections/test-collection/documents",
        json={
            "payload": {"original_document_name": "text1.txt", "document_name": "text1.txt"},
            "errorMessages": [],
        },
    )
    file_path = os.path.join(TEST_DIRECTORY, "resources/texts/text1.txt")
    with open(file_path, "r", encoding="UTF-8") as input_io:
        # Please note that we do not set mime_type = plain/text here, but it is automatically inferred
        result = document_collection.import_documents(input_io)

    assert result[0]["document_name"] == "text1.txt"


def test_import_cas(document_collection, requests_mock):
    requests_mock.post(
        f"{API_BASE}/importer/projects/{PROJECT_NAME}/documentCollections/test-collection/documents",
        json={
            "payload": {"original_document_name": "text1.xmi", "document_name": "text1.xmi"},
            "errorMessages": [],
        },
    )

    cas = Cas(typesystem=TypeSystem())

    result = document_collection.import_documents(cas, filename="text1.xmi")

    assert result[0]["document_name"] == "text1.xmi"


def test_import_solr_xml(document_collection, requests_mock):
    requests_mock.post(
        f"{API_BASE}/importer/projects/{PROJECT_NAME}/documentCollections/test-collection/documents",
        json={
            "payload": [
                {
                    "original_document_name": "disease_solr-1.xml",
                    "document_name": "disease_solr-1.xml",
                },
                {
                    "original_document_name": "disease_solr-2.xml",
                    "document_name": "disease_solr-2.xml",
                },
            ],
            "errorMessages": [],
        },
    )
    file_path_xml = Path(TEST_DIRECTORY, "resources/xml/disease_solr.xml")

    # Please note that it only works for solr-xml, if we explicitly set the mime-type
    result = document_collection.import_documents(
        file_path_xml, mime_type="application/vnd.averbis.solr+xml"
    )

    assert result[0]["document_name"] == "disease_solr-1.xml"
    assert result[1]["document_name"] == "disease_solr-2.xml"

    # Otherwise, we get a ValueError
    with pytest.raises(ValueError):
        document_collection.import_documents(file_path_xml)


def test_create_and_run_process(document_collection, requests_mock):
    pipeline_name = "test-pipeline"
    process_name = "test-process"
    state = "IDLE"
    number_of_documents = 12

    requests_mock.post(
        f"{API_EXPERIMENTAL}/textanalysis/projects/{PROJECT_NAME}/processes",
        headers={"Content-Type": "application/json"},
        json={"payload": None, "errorMessages": []},
    )

    requests_mock.get(
        f"{API_EXPERIMENTAL}/textanalysis/projects/{PROJECT_NAME}/"
        f"documentSources/{document_collection.name}/processes/{process_name}",
        headers={"Content-Type": "application/json"},
        json={
            "payload": {
                "processName": process_name,
                "pipelineName": pipeline_name,
                "documentSourceName": document_collection.name,
                "state": state,
                "processedDocuments": number_of_documents,
            },
            "errorMessages": [],
        },
    )

    actual_process = document_collection.create_and_run_process(
        process_name=process_name, pipeline=pipeline_name
    )

    expected_process = Process(
        document_collection.project, process_name, document_collection.name, pipeline_name
    )
    assert_process_equal(expected_process, actual_process)


def test_list_processes(client_version_6, requests_mock):
    project = client_version_6.get_project(PROJECT_NAME)
    document_collection = DocumentCollection(project, "my_collection")
    pipeline_name = "my_pipeline_name"
    state = "IDLE"

    all_processes_payload = [
        {"processName": "process1", "documentSourceName": "my_collection"},
        {"processName": "process2", "documentSourceName": "document_source_2"},
        {"processName": "process3", "documentSourceName": "document_source_3"},
    ]

    expected_processes = []
    for i, item in enumerate(all_processes_payload):
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
        f"{API_EXPERIMENTAL}/textanalysis/projects/{PROJECT_NAME}/processes",
        headers={"Content-Type": "application/json"},
        json={"payload": all_processes_payload, "errorMessages": []},
    )

    for i, item in enumerate(all_processes_payload):
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
            f"{API_EXPERIMENTAL}/textanalysis/projects/{PROJECT_NAME}/"
            f"documentSources/{document_source_name}/processes/{process_name}",
            headers={"Content-Type": "application/json"},
            json={"payload": payload, "errorMessages": []},
        )

    actual_processes = document_collection.list_processes()
    assert len(actual_processes) == 1

    assert actual_processes[0].name == "process1"
    assert actual_processes[0].project.name == PROJECT_NAME
    assert actual_processes[0].pipeline_name == "my_pipeline_name"
    assert actual_processes[0].document_source_name == "my_collection"


def test_get_process(client_version_6, requests_mock):
    project = client_version_6.get_project(PROJECT_NAME)
    process_name = "my_process"
    document_source_name = "my_document_source"
    pipeline_name = "my_pipeline_name"

    expected_process = Process(project, process_name, document_source_name, pipeline_name)

    payload = {
        "processName": process_name,
        "pipelineName": pipeline_name,
        "documentSourceName": document_source_name,
        "state": "IDLE",
        "processedDocuments": 12,
    }

    requests_mock.get(
        f"{API_EXPERIMENTAL}/textanalysis/projects/{PROJECT_NAME}/"
        f"documentSources/{document_source_name}/processes/{process_name}",
        headers={"Content-Type": "application/json"},
        json={"payload": payload, "errorMessages": []},
    )
    actual = project.get_document_collection(document_source_name).get_process(process_name)
    assert_process_equal(expected_process, actual)
