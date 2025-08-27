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
import tempfile
from pathlib import Path

from cassis import Cas, TypeSystem, load_typesystem

from averbis import Project, Pipeline
from averbis.core import OperationNotSupported, MEDIA_TYPE_APPLICATION_XMI, EvaluationConfiguration
from tests.fixtures import *
from tests.utils import *


@pytest.fixture()
def process(client) -> Process:
    project = client.get_project(PROJECT_NAME)
    return Process(project, "my_process", "my_doc_source", "my_pipeline")


def test_delete(process, requests_mock):
    requests_mock.delete(
        f"{API_EXPERIMENTAL}/textanalysis/projects/{PROJECT_NAME}/"
        f"documentSources/{process.document_source_name}/processes/{process.name}",
        headers={"Content-Type": "application/json"},
        json={"payload": None, "errorMessages": []},
    )

    process.delete()

def test_process_unprocessed_not_supported(process, requests_mock):
    with pytest.raises(OperationNotSupported):
        process.process_unprocessed()

def test_process_unprocessed(client_version_8, requests_mock):
    project = client_version_8.get_project(PROJECT_NAME)
    process = Process(project, "my_process", "my_doc_source", "my_pipeline")
    requests_mock.post(
        f"{API_EXPERIMENTAL}/textanalysis/projects/{PROJECT_NAME}/"
        f"documentSources/{process.document_source_name}/processes/{process.name}/reprocessUnprocessed",
        headers={"Content-Type": "application/json"},
        json={"payload": None, "errorMessages": []}
    )
    
    process.process_unprocessed()


def test_rerun(process, requests_mock):
    requests_mock.post(
        f"{API_EXPERIMENTAL}/textanalysis/projects/{PROJECT_NAME}/"
        f"documentSources/{process.document_source_name}/processes/{process.name}/reprocess",
        headers={"Content-Type": "application/json"},
        json={"payload": None, "errorMessages": []},
    )

    process.rerun()

def test_rerun_document_names_not_supported(process):
    with pytest.raises(OperationNotSupported):
        process.rerun(document_names=["doc1.txt", "doc2.txt"])


def test_rerun_document_names(client_version_8, requests_mock):
    project = client_version_8.get_project(PROJECT_NAME)
    process = Process(project, "my_process", "my_doc_source", "my_pipeline")
    
    expected_document_names = ["doc1.txt", "doc2.txt"]

    captured_document_names = []
    def callback(request, _content):
        captured_document_names.extend(request.json()["documentNames"])
        return {"payload": None, "errorMessages": []}
    
    requests_mock.post(
        f"{API_EXPERIMENTAL}/textanalysis/projects/{PROJECT_NAME}/"
        f"documentSources/{process.document_source_name}/processes/{process.name}/reprocess",
        headers={"Content-Type": "application/json"},
        json=callback,
    )

    process.rerun(document_names=expected_document_names)
    assert captured_document_names == expected_document_names


def test_create_and_run_process(process, requests_mock):
    process_name = "process-on-process"
    pipeline_name = "second-pipeline"

    requests_mock.post(
        f"{API_EXPERIMENTAL}/textanalysis/projects/{process.project.name}/processes",
        headers={"Content-Type": "application/json"},
        json={"payload": None, "errorMessages": []},
    )

    payload = {
        "processName": process_name,
        "pipelineName": pipeline_name,
        "documentSourceName": process.document_source_name,
        "state": "IDLE",
        "processedDocuments": 12,
        "precedingProcessName": process.name,
    }

    requests_mock.get(
        f"{API_EXPERIMENTAL}/textanalysis/projects/{PROJECT_NAME}/"
        f"documentSources/{process.document_source_name}/processes/{process_name}",
        headers={"Content-Type": "application/json"},
        json={"payload": payload, "errorMessages": []},
    )

    actual_process_with_preceding_process = process.create_and_run_process(
        process_name, pipeline_name
    )

    expected_process = Process(
        process.project,
        process_name,
        process.document_source_name,
        pipeline_name,
        preceding_process_name=process.name,
    )

    assert_process_equal(actual_process_with_preceding_process, expected_process)


def test_deprecated_process_state(process, requests_mock):
    # todo: delete me when v6 is released
    payload = {
        "processName": process.name,
        "pipelineName": process.pipeline_name,
        "documentSourceName": process.document_source_name,
        "state": "IDLE",
        "processedDocuments": 12,
    }

    requests_mock.get(
        f"{API_EXPERIMENTAL}/textanalysis/projects/{PROJECT_NAME}/"
        f"documentSources/{process.document_source_name}/processes/{process.name}",
        headers={"Content-Type": "application/json"},
        json={"payload": payload, "errorMessages": []},
    )

    process_dto = process.get_process_state()
    assert process_dto.processed_documents == 12


def test_process_state(process, requests_mock):
    payload = {
        "processName": process.name,
        "pipelineName": process.pipeline_name,
        "documentSourceName": process.document_source_name,
        "state": "IDLE",
        "numberOfTotalDocuments": 6871,
        "numberOfSuccessfulDocuments": 6871,
        "numberOfUnsuccessfulDocuments": 0,
        "errorMessages": [],
    }

    requests_mock.get(
        f"{API_EXPERIMENTAL}/textanalysis/projects/{PROJECT_NAME}/"
        f"documentSources/{process.document_source_name}/processes/{process.name}",
        headers={"Content-Type": "application/json"},
        json={"payload": payload, "errorMessages": []},
    )

    process_dto = process.get_process_state()
    assert process_dto.processed_documents is None
    assert process_dto.state == "IDLE"


def test_export_text_analysis_export_v5(client_version_5):
    process = Process(
        project=Project(client_version_5, PROJECT_NAME),
        name="my-process",
        pipeline_name="my-pipeline",
        document_source_name=COLLECTION_NAME,
    )

    with pytest.raises(OperationNotSupported):
        process.export_text_analysis()


def test_export_text_analysis_export_v6(client_version_6, requests_mock):
    project = Project(client_version_6, PROJECT_NAME)
    collection = project.get_document_collection(COLLECTION_NAME)
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

    process = collection.get_process(process_name)

    requests_mock.get(
        f"{API_BASE}/textanalysis/projects/{project.name}/"
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
                        ],
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


def test_export_text_analysis_with_page_and_pagsize(client_version_6, requests_mock):
    project = Project(client_version_6, PROJECT_NAME)
    collection = project.get_document_collection(COLLECTION_NAME)
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
                # Truncated
            },
            "errorMessages": [],
        },
    )
    process = collection.get_process(process_name)

    def callback(request, _content):
        page_size = int(request.qs["pageSize"][0])
        page = int(request.qs["page"][0])
        return_payload = [
            {"documentName": f"Document ({page_size * (page - 1) + k}).txt", "annotationDtos": []}
            for k in range(1, page_size + 1)
        ]
        return {
            "payload": {
                "textAnalysisResultDtos": return_payload,
                "projectName": project.name,
                # Truncated
            },
            "errorMessages": [],
        }

    requests_mock.get(
        f"{API_BASE}/textanalysis/projects/{project.name}/"
        f"documentSources/{process.document_source_name}/processes/{process.name}/export",
        headers={"Content-Type": "application/json"},
        json=callback,
    )

    export1 = process.export_text_analysis(page_size=4, page=1)
    assert len(export1["textAnalysisResultDtos"]) == 4
    assert export1["textAnalysisResultDtos"][0]["documentName"] == "Document (1).txt"

    export2 = process.export_text_analysis(page_size=4, page=2)
    assert len(export2["textAnalysisResultDtos"]) == 4
    assert export2["textAnalysisResultDtos"][-1]["documentName"] == "Document (8).txt"

    export3 = process.export_text_analysis(page=2)
    assert len(export3["textAnalysisResultDtos"]) == 100
    assert export3["textAnalysisResultDtos"][-1]["documentName"] == "Document (200).txt"

def test_export_text_analysis_document_selection(client_version_8, requests_mock):
    project = Project(client_version_8, PROJECT_NAME)
    collection = project.get_document_collection(COLLECTION_NAME)
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
                # Truncated
            },
            "errorMessages": [],
        },
    )
    process = collection.get_process(process_name)
    actual_document_names = []
    def callback(request, _content):
        actual_document_names.extend(request.json()["documentNames"])
        return {
            "payload": {
                "textAnalysisResultDtos": [
                    {"documentName": name, "annotationDtos": []} for name in actual_document_names
                ],
                "projectName": project.name,
                # Truncated
            },
            "errorMessages": [],
        }

    requests_mock.post(
        f"{API_EXPERIMENTAL}/textanalysis/projects/{project.name}/"
        f"documentCollections/{process.document_source_name}/processes/{process.name}/export",
        headers={"Content-Type": "application/json"},
        json=callback,
    )
    expected_document_names = ["text1.txt", "text2.txt"]
    export = process.export_text_analysis(document_names=expected_document_names)
    textanalysis_results = export["textAnalysisResultDtos"]
    assert len(textanalysis_results) == len(expected_document_names)
    assert all(result["documentName"] in expected_document_names for result in textanalysis_results)

def test_export_text_analysis_document_selection_not_supported(client_version_7, requests_mock):
    project = Project(client_version_7, PROJECT_NAME)
    collection = project.get_document_collection(COLLECTION_NAME)
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
                # Truncated
            },
            "errorMessages": [],
        },
    )
    process = collection.get_process(process_name)

    with pytest.raises(OperationNotSupported):
        process.export_text_analysis(document_names=["text1.txt", "text2.txt"])


def test_export_text_analysis_to_cas_v5(client_version_5):
    document_name = "document0001.txt"
    process = Process(
        project=Project(client_version_5, PROJECT_NAME),
        name="my-process",
        pipeline_name="my-pipeline",
        document_source_name=COLLECTION_NAME,
    )

    with pytest.raises(OperationNotSupported):
        process.export_text_analysis_to_cas(document_name)


def test_export_text_analysis_to_cas_v6_full_name_support(
    client_version_6_17_platform_6_50, requests_mock
):
    project = client_version_6_17_platform_6_50.get_project(PROJECT_NAME)
    collection = project.get_document_collection(COLLECTION_NAME)
    document_name = "document.txt"
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
        f"{API_EXPERIMENTAL}/textanalysis/projects/{project.name}/documentCollections/{collection.name}"
        f"/processes/{process.name}/textAnalysisResultTypeSystem",
        headers={"Content-Type": "application/xml"},
        text=empty_typesystem,
    )

    requests_mock.get(
        f"{API_EXPERIMENTAL}/textanalysis/projects/{project.name}/documentCollections/{collection.name}"
        f"/processes/{process.name}/textAnalysisResult",
        headers={"Content-Type": "application/vnd.uima.cas+xmi"},
        text=expected_xmi,
    )

    cas = process.export_text_analysis_to_cas(document_name)

    assert cas.sofa_string == "Test"


def test_export_text_analysis_to_cas_v6_onlycas_export_by_name_support(
    client_version_6_7, requests_mock
):
    project = client_version_6_7.get_project(PROJECT_NAME)
    collection = project.get_document_collection(COLLECTION_NAME)
    document_id = "document0001"
    document_name = "document.txt"
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
        f"{API_EXPERIMENTAL}/textanalysis/projects/{project.name}/documentCollections/{collection.name}"
        f"/documents/{document_id}/processes/{process.name}/exportTextAnalysisResultTypeSystem",
        headers={"Content-Type": "application/xml"},
        text=empty_typesystem,
    )

    requests_mock.get(
        f"{API_EXPERIMENTAL}/projects/{project.name}/documentCollections/{collection.name}/documents",
        headers={"Content-Type": "application/json"},
        json={
            "payload": [{"documentIdentifier": document_id, "documentName": document_name}],
            "errorMessages": [],
        },
    )
    requests_mock.get(
        f"{API_EXPERIMENTAL}/textanalysis/projects/{project.name}/documentCollections/{collection.name}"
        f"/processes/{process.name}/textAnalysisResult",
        headers={"Content-Type": "application/vnd.uima.cas+xmi"},
        text=expected_xmi,
    )

    cas = process.export_text_analysis_to_cas(document_name)

    assert cas.sofa_string == "Test"


def test_export_text_analysis_to_cas_v6_only_id_support(client_version_6, requests_mock):
    project = client_version_6.get_project(PROJECT_NAME)
    collection = project.get_document_collection(COLLECTION_NAME)
    document_id = "document0001"
    document_name = "document.txt"
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
        f"{API_EXPERIMENTAL}/textanalysis/projects/{project.name}/documentCollections/{collection.name}"
        f"/processes/{process.name}/textAnalysisResultTypeSystem",
        headers={"Content-Type": "application/xml"},
        text=empty_typesystem,
        status_code=405,
    )

    requests_mock.get(
        f"{API_EXPERIMENTAL}/textanalysis/projects/{project.name}/documentCollections/{collection.name}"
        f"/documents/{document_id}/processes/{process.name}/exportTextAnalysisResultTypeSystem",
        headers={"Content-Type": "application/xml"},
        text=empty_typesystem,
    )

    requests_mock.get(
        f"{API_EXPERIMENTAL}/projects/{project.name}/documentCollections/{collection.name}/documents",
        headers={"Content-Type": "application/json"},
        json={
            "payload": [{"documentIdentifier": document_id, "documentName": document_name}],
            "errorMessages": [],
        },
    )

    requests_mock.get(
        f"{API_EXPERIMENTAL}/textanalysis/projects/{project.name}/documentCollections/{collection.name}"
        f"/processes/{process.name}/textAnalysisResult",
        headers={"Content-Type": "application/vnd.uima.cas+xmi"},
        text=expected_xmi,
        status_code=405,
    )

    requests_mock.get(
        f"{API_EXPERIMENTAL}/textanalysis/projects/{project.name}/documentCollections/{collection.name}"
        f"/documents/{document_id}/processes/{process.name}/exportTextAnalysisResult",
        headers={"Content-Type": "application/vnd.uima.cas+xmi"},
        text=expected_xmi,
    )

    cas = process.export_text_analysis_to_cas(document_name)

    assert cas.sofa_string == "Test"


def test_export_text_analysis_to_cas_v6_7_provide_typesystem(client_version_6_7, requests_mock):
    project = client_version_6_7.get_project(PROJECT_NAME)
    collection = project.get_document_collection(COLLECTION_NAME)
    document_id = "document0001"
    document_name = "document.txt"
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
    cas_typesystem = load_typesystem(empty_typesystem)
    pipeline = Pipeline(project, "my-pipeline")
    process = Process(project, "my-process", collection.name, pipeline.name)

    requests_mock.get(
        f"{API_EXPERIMENTAL}/projects/{project.name}/documentCollections/{collection.name}/documents",
        headers={"Content-Type": "application/json"},
        json={
            "payload": [{"documentIdentifier": document_id, "documentName": document_name}],
            "errorMessages": [],
        },
    )

    requests_mock.get(
        f"{API_EXPERIMENTAL}/textanalysis/projects/{project.name}/documentCollections/{collection.name}"
        f"/processes/{process.name}/textAnalysisResult",
        headers={"Content-Type": "application/vnd.uima.cas+xmi"},
        text=expected_xmi,
    )

    cas = process.export_text_analysis_to_cas(document_name, type_system=cas_typesystem)

    assert cas.sofa_string == "Test"


def test_export_text_analysis_to_cas_annotation_types_not_supported(
    client_version_6_17_0_platform_6_48_0, requests_mock
):
    project = client_version_6_17_0_platform_6_48_0.get_project(PROJECT_NAME)
    collection = project.get_document_collection(COLLECTION_NAME)
    document_id = "document0001"
    document_name = "document.txt"
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
    cas_typesystem = load_typesystem(empty_typesystem)
    pipeline = Pipeline(project, "my-pipeline")
    process = Process(project, "my-process", collection.name, pipeline.name)

    requests_mock.get(
        f"{API_EXPERIMENTAL}/projects/{project.name}/documentCollections/{collection.name}/documents",
        headers={"Content-Type": "application/json"},
        json={
            "payload": [{"documentIdentifier": document_id, "documentName": document_name}],
            "errorMessages": [],
        },
    )

    requests_mock.get(
        f"{API_EXPERIMENTAL}/textanalysis/projects/{project.name}/documentCollections/{collection.name}"
        f"/processes/{process.name}/textAnalysisResult",
        headers={"Content-Type": "application/vnd.uima.cas+xmi"},
        text=expected_xmi,
    )

    cas = process.export_text_analysis_to_cas(
        document_name,
        type_system=cas_typesystem,
        annotation_types="de.averbis.types.health.Diagnosis",
    )

    assert cas.sofa_string == "Test"


def test_add_text_analysis_result_cas(client_version_6, requests_mock):
    project = client_version_6.get_project(PROJECT_NAME)
    collection = project.get_document_collection(COLLECTION_NAME)
    process = Process(project, "my-process", collection.name)
    cas = Cas(typesystem=TypeSystem())
    document_name = "my-document.txt"

    requests_mock.post(
        f"{API_EXPERIMENTAL}/textanalysis/projects/{project.name}/documentCollections/{collection.name}/processes/{process.name}/textAnalysisResult",
        headers={"Content-Type": "application/json"},
        json={"payload": None, "errorMessages": []},
    )
    process.import_text_analysis_result(cas, document_name)


def test_update_text_analysis_result_cas(client_version_6, requests_mock):
    project = client_version_6.get_project(PROJECT_NAME)
    collection = project.get_document_collection(COLLECTION_NAME)
    process = Process(project, "my-process", collection.name)
    cas = Cas(typesystem=TypeSystem())
    document_name = "my-document.txt"

    requests_mock.put(
        f"{API_EXPERIMENTAL}/textanalysis/projects/{project.name}/documentCollections/{collection.name}/processes/{process.name}/textAnalysisResult",
        headers={"Content-Type": "application/json"},
        json={"payload": None, "errorMessages": []},
    )
    process.import_text_analysis_result(cas, document_name, process.name, overwrite=True)


def test_add_text_analysis_result_cas_file(client_version_6, requests_mock):
    project = client_version_6.get_project(PROJECT_NAME)
    collection = project.get_document_collection(COLLECTION_NAME)
    process = Process(project, "my-process", collection.name)
    typesystem = TypeSystem()
    test_xmi = b"""<?xml version="1.0" encoding="UTF-8"?>
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
    document_name = "my-document.txt"

    requests_mock.post(
        f"{API_EXPERIMENTAL}/textanalysis/projects/{project.name}/documentCollections/{collection.name}/processes/{process.name}/textAnalysisResult",
        headers={"Content-Type": "application/json"},
        json={"payload": None, "errorMessages": []},
    )

    with tempfile.NamedTemporaryFile() as tmp_file:
        tmp_file.write(test_xmi)
        process.import_text_analysis_result(
            Path(tmp_file.name),
            document_name,
            mime_type=MEDIA_TYPE_APPLICATION_XMI,
            typesystem=typesystem,
        )

        # should raise exception because typesystem is not given
        with pytest.raises(Exception):
            process.import_text_analysis_result(
                Path(tmp_file.name), document_name, mime_type=MEDIA_TYPE_APPLICATION_XMI
            )
        # should raise exception because mime type is not given
        with pytest.raises(Exception):
            process.import_text_analysis_result(
                Path(tmp_file.name), document_name, typesystem=typesystem
            )


def test_evaluate(client_version_6, requests_mock):
    project = client_version_6.get_project(PROJECT_NAME)
    collection = project.get_document_collection(COLLECTION_NAME)
    comparison_process = Process(project, "comparison-process", collection.name)
    reference_process = Process(project, "reference-process", collection.name)
    evaluation_process_name = "evaluation_process"
    requests_mock.post(
        f"{API_EXPERIMENTAL}/textanalysis/projects/{project.name}/documentCollections/{collection.name}/evaluationProcesses",
        headers={"Content-Type": "application/json"},
        json={"payload": None, "errorMessages": []},
    )
    list_processes_payload = [
        {"processName": evaluation_process_name, "documentSourceName": collection.name}
    ]
    requests_mock.get(
        f"{API_EXPERIMENTAL}/textanalysis/projects/{project.name}/processes",
        json={"payload": list_processes_payload, "errorMessages": []},
    )

    clinical_section_keyword_config = EvaluationConfiguration(
        "de.averbis.types.health.ClinicalSectionKeyword", ["begin", "end"]
    )
    medication_keyword_config = (
        EvaluationConfiguration("de.averbis.types.health.Medication", ["begin", "end"])
        .add_feature("drugs")
        .use_range_variance_partial_match(3)
    )
    evaluation_process = comparison_process.evaluate_against(
        reference_process,
        evaluation_process_name,
        [clinical_section_keyword_config, medication_keyword_config],
    )

    assert evaluation_process.name == evaluation_process_name
    assert evaluation_process.document_source_name == collection.name


def test_rename_process(process, requests_mock):
    new_name = "renamed_process"

    requests_mock.post(
        f"{API_EXPERIMENTAL}/textanalysis/projects/{process.project.name}/documentCollections/{process.document_source_name}/processes/{process.name}",
        headers={"Content-Type": "text/plain; charset=utf-8"},
        json={"payload": None, "errorMessages": []},
    )

    actual_renamed_process = process.rename(new_name)

    expected_process = Process(
        process.project,
        new_name,
        process.document_source_name,
        process.pipeline_name,
    )

    assert_process_equal(actual_renamed_process, expected_process)
