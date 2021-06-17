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
from averbis import Process
from tests.fixtures import *


@pytest.fixture()
def process(client) -> Process:
    project = client.get_project("test-project")
    return Process(project, "my_process", "my_doc_source", "my_pipeline")


def test_delete(process, requests_mock):

    requests_mock.delete(
        f"{API_EXPERIMENTAL}/textanalysis/projects/test-project/"
        f"documentSources/{process.document_source_name}/processes/{process.name}",
        headers={"Content-Type": "application/json"},
        json={"payload": None, "errorMessages": []},
    )

    process.delete()


def test_rerun(process, requests_mock):

    requests_mock.post(
        f"{API_EXPERIMENTAL}/textanalysis/projects/test-project/"
        f"documentSources/{process.document_source_name}/processes/{process.name}/reprocess",
        headers={"Content-Type": "application/json"},
        json={"payload": None, "errorMessages": []},
    )

    process.rerun()


def test_deprecated_process_state(process, requests_mock):
    # todo: delete me when v6 is released

    state = "IDLE"
    number_of_documents = 12

    payload = {
        "processName": process.name,
        "pipelineName": process.pipeline_name,
        "documentSourceName": process.document_source_name,
        "state": state,
        "processedDocuments": number_of_documents,
    }

    requests_mock.get(
        f"{API_EXPERIMENTAL}/textanalysis/projects/test-project/"
        f"documentSources/{process.document_source_name}/processes/{process.name}",
        headers={"Content-Type": "application/json"},
        json={"payload": payload, "errorMessages": []},
    )

    process_dto = process.get_process_state()
    assert process_dto.processed_documents == 12


def test_process_state(process, requests_mock):
    state = "IDLE"

    payload = {
        "processName": process.name,
        "pipelineName": process.pipeline_name,
        "documentSourceName": process.document_source_name,
        "state": state,
        "numberOfTotalDocuments": 6871,
        "numberOfSuccessfulDocuments": 6871,
        "numberOfUnsuccessfulDocuments": 0,
        "errorMessages": [],
        "precedingProcessName": "precedingProcessName",
    }

    requests_mock.get(
        f"{API_EXPERIMENTAL}/textanalysis/projects/test-project/"
        f"documentSources/{process.document_source_name}/processes/{process.name}",
        headers={"Content-Type": "application/json"},
        json={"payload": payload, "errorMessages": []},
    )

    process_dto = process.get_process_state()
    assert process_dto.processed_documents is None
    assert process_dto.preceding_process_name == "precedingProcessName"
    assert process_dto.state == "IDLE"
