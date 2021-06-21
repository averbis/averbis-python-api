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
from cassis import Cas, TypeSystem

from averbis import Process, Project, Pipeline
from averbis.core import OperationNotSupported
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


def test_export_text_analysis_export_v5(client_version_5):
    process = Process(
        project=Project(client_version_5, "LoadTesting"),
        name="my-process",
        pipeline_name="my-pipeline",
        document_source_name="my-collection",
    )

    with pytest.raises(OperationNotSupported):
        process.export_text_analysis()


def test_export_text_analysis_export_v6(client_version_6, requests_mock):
    project = Project(client_version_6, "LoadTesting")
    collection = project.get_document_collection("my-collection")
    process_name = "my-process"

    requests_mock.get(
        f"{API_EXPERIMENTAL}/textanalysis/projects/{project.name}/"
        f"documentSources/{collection.name}/processes/{process_name}",
        headers={"Content-Type": "application/json"},
        json={
            "payload": {
                "processName": process_name,
                "pipelineName": "my-pipeline",
                "documentSourceName": collection.name,
                "state": "IDLE",
                "numberOfTotalDocuments": 6871,
                "numberOfSuccessfulDocuments": 6871,
                "numberOfUnsuccessfulDocuments": 0,
                "errorMessages": [],
                "precedingProcessName": "precedingProcessName",
            },
            "errorMessages": [],
        },
    )

    process = project.get_process(process_name, collection)

    requests_mock.get(
        f"{API_EXPERIMENTAL}/textanalysis/projects/{project.name}/"
        f"documentSources/{process.document_source_name}/processes/{process.name}/export",
        headers={"Content-Type": "application/json"},
        json={
            "payload": {
                "projectName": project.name,
                "documentSourceName": collection.name,
                "textAnalysisResultSetName": process.name,
                "pipelineName": "discharge",
                "textAnalysisResultDtos": [
                    {
                        "documentName": "abcdef.txt",
                        "annotationDtos": [
                            {
                                "begin": 0,
                                "end": 12,
                                "type": "uima.tcas.DocumentAnnotation",
                                "coveredText": "Hello World",
                                "id": 66753,
                            }
                        ]
                        # truncated #
                    }
                    # truncated #
                ],
            },
            "errorMessages": [],
        },
    )
    export = process.export_text_analysis()
    assert export["documentSourceName"] == collection.name


def test_export_text_analysis_to_cas_v5(client_version_5):
    document_id = "document0001"
    process = Process(
        project=Project(client_version_5, "LoadTesting"),
        name="my-process",
        pipeline_name="my-pipeline",
        document_source_name="my-collection",
    )

    with pytest.raises(OperationNotSupported):
        process.export_text_analysis_to_cas(document_id)


def test_export_text_analysis_to_cas_v6(client_version_6, requests_mock):
    project = client_version_6.get_project("LoadTesting")
    collection = project.get_document_collection("my-collection")
    document_id = "document0001"
    expected_xmi = """<?xml version="1.0" encoding="UTF-8"?>
        <xmi:XMI xmlns:tcas="http:///uima/tcas.ecore" xmlns:xmi="http://www.omg.org/XMI" 
        xmlns:cas="http:///uima/cas.ecore"
                 xmi:version="2.0">
            <cas:NULL xmi:id="0"/>
            <tcas:DocumentAnnotation xmi:id="2" sofa="1" begin="0" end="4" language="x-unspecified"/>
            <cas:Sofa xmi:id="1" sofaNum="1" sofaID="_InitialView" mimeType="text/plain"
                      sofaString="Test"/>
            <cas:View sofa="1" members="2"/>
        </xmi:XMI>
        """
    empty_typesystem = '<typeSystemDescription xmlns="http://uima.apache.org/resourceSpecifier"/>'
    pipeline = Pipeline(project, "my-pipeline")
    process = Process(project, "my-process", collection.name, pipeline.name)

    requests_mock.get(
        f"{API_EXPERIMENTAL}/textanalysis/projects/{project.name}/pipelines/{pipeline.name}/exportTypesystem",
        headers={"Content-Type": "text/xml"},
        text=empty_typesystem,
    )

    requests_mock.get(
        f"{API_EXPERIMENTAL}/textanalysis/projects/{project.name}/documentCollections/{collection.name}"
        f"/documents/{document_id}/processes/{process.name}/exportTextAnalysisResult",
        headers={"Content-Type": "application/vnd.uima.cas+xmi"},
        text=expected_xmi,
    )

    cas = process.export_text_analysis_to_cas(document_id)

    assert cas.sofa_string == "Test"
