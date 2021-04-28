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
from pathlib import Path

from averbis import Pipeline, Project
from averbis.core import (
    OperationNotSupported,
    TERMINOLOGY_EXPORTER_OBO_1_4,
    TERMINOLOGY_IMPORTER_OBO,
    ENCODING_UTF_8,
    DOCUMENT_IMPORTER_TEXT,
)
from tests.fixtures import *


TEST_DIRECTORY = os.path.dirname(__file__)

logging.basicConfig(level=logging.INFO)


def test_default_headers(client):
    client._api_token = TEST_API_TOKEN
    headers = client._default_headers()

    assert headers["Accept"] == "application/json"
    assert TEST_API_TOKEN == headers["api-token"]


def test_default_headers_with_override(client):
    headers = client._default_headers({"Content-Type": "text/plain"})

    assert headers["Accept"] == "application/json"
    assert headers["Content-Type"] == "text/plain"


def test_change_password(client, requests_mock):
    requests_mock.put(
        f"{API_BASE}/users/admin/changeMyPassword",
        headers={"Content-Type": "application/json"},
        json={"payload": None, "errorMessages": []},
    )

    client.change_password("admin", "admin", "admin")


def test_generate_api_token(client, requests_mock):
    requests_mock.post(
        f"{API_BASE}/users/admin/apitoken",
        headers={"Content-Type": "application/json"},
        json={
            "payload": TEST_API_TOKEN,
            "errorMessages": [],
        },
    )

    api_token = client.generate_api_token("admin", "admin")
    headers = client._default_headers()

    assert TEST_API_TOKEN == api_token
    assert TEST_API_TOKEN == client._api_token
    assert TEST_API_TOKEN == headers["api-token"]


def test_regenerate_api_token(client, requests_mock):
    requests_mock.put(
        f"{API_BASE}/users/admin/apitoken",
        headers={"Content-Type": "application/json"},
        json={
            "payload": TEST_API_TOKEN,
            "errorMessages": [],
        },
    )

    api_token = client.regenerate_api_token("admin", "admin")
    headers = client._default_headers()

    assert TEST_API_TOKEN == api_token
    assert TEST_API_TOKEN == client._api_token
    assert TEST_API_TOKEN == headers["api-token"]


def test_invalidate_api_token(client, requests_mock):
    requests_mock.delete(
        f"{API_BASE}/users/admin/apitoken",
        headers={"Content-Type": "application/json"},
        json={
            "payload": None,
            "errorMessages": [],
        },
    )

    response = client.invalidate_api_token("admin", "admin")

    assert response is None


def test_get_api_token_status(client, requests_mock):
    requests_mock.post(
        f"{API_BASE}/users/admin/apitoken/status",
        headers={"Content-Type": "application/json"},
        json={
            "payload": "GENERATED",
            "errorMessages": [],
        },
    )

    status = client.get_api_token_status("admin", "admin")

    assert status == "GENERATED"


def test_get_build_info(client, requests_mock):
    requests_mock.get(
        f"{API_BASE}/buildInfo",
        headers={"Content-Type": "application/json"},
        json={"payload": {"specVersion": "5.33.0", "buildNumber": ""}, "errorMessages": []},
    )

    build_info = client.get_build_info()

    assert build_info["specVersion"] == "5.33.0"
    assert build_info["buildNumber"] == ""


def test_create_project(client, requests_mock):
    def callback(request, _):
        return {
            "payload": {
                "id": 93498,
                "name": request.qs["name"][0],
                "description": request.qs["description"][0],
            },
            "errorMessages": [],
        }

    requests_mock.post(
        f"{API_BASE}/projects", headers={"Content-Type": "application/json"}, json=callback
    )

    project = client.create_project("LoadTesting", "Project for load testing")

    assert project.name == "LoadTesting"


def test_get_project(client):
    project = client.get_project("LoadTesting")

    assert project.name == "LoadTesting"


def test_list_projects(client, requests_mock):
    def callback(request, _):
        return {
            "payload": [
                {"name": "Jumble", "description": ""},
                {"name": "Bumble", "description": ""},
            ],
            "errorMessages": [],
        }

    requests_mock.get(
        f"{API_EXPERIMENTAL}/projects", headers={"Content-Type": "application/json"}, json=callback
    )

    project_list = client.list_projects()

    assert project_list[0]["name"] == "Jumble"
    assert project_list[1]["name"] == "Bumble"


def test_delete_projects(client):
    with pytest.raises(OperationNotSupported):
        client._delete_project("LoadTesting")


def test_create_pipeline(client, requests_mock):
    requests_mock.post(
        f"{API_BASE}/textanalysis/projects/LoadTesting/pipelines",
        headers={"Content-Type": "application/json"},
        json={"payload": None, "errorMessages": []},
    )

    configuration = {
        "schemaVersion": "1.3",
        "name": "discharge",
        "description": None,
        "analysisEnginePoolSize": 1,
        "casPoolSize": 2,
        # ... truncated ...
    }

    new_pipeline = client._create_pipeline("LoadTesting", configuration)

    assert new_pipeline is None


def test_create_pipeline_schema_version_two(client, requests_mock):
    requests_mock.post(
        f"{API_BASE}/textanalysis/projects/LoadTesting/pipelines",
        headers={"Content-Type": "application/json"},
        json={"payload": None, "errorMessages": []},
    )

    configuration = {
        "schemaVersion": "2.0",
        "pipelineName": "discharge",
        "description": None,
        "numberOfInstances": 2,
        # ... truncated ...
    }

    new_pipeline = client._create_pipeline("LoadTesting", configuration)

    assert new_pipeline is None


def test_start_pipeline(client, requests_mock):
    requests_mock.put(
        f"{API_BASE}/textanalysis/projects/LoadTesting/pipelines/discharge/start",
        headers={"Content-Type": "application/json"},
        json={"payload": None, "errorMessages": []},
    )

    response = client._start_pipeline("LoadTesting", "discharge")

    assert response is None


def test_stop_pipeline(client, requests_mock):
    requests_mock.put(
        f"{API_BASE}/textanalysis/projects/LoadTesting/pipelines/discharge/stop",
        headers={"Content-Type": "application/json"},
        json={"payload": None, "errorMessages": []},
    )

    response = client._stop_pipeline("LoadTesting", "discharge")

    assert response is None


def test_get_pipeline_info(client, requests_mock):
    requests_mock.get(
        f"{API_BASE}/textanalysis/projects/LoadTesting/pipelines/discharge",
        headers={"Content-Type": "application/json"},
        json={
            "payload": {
                "id": 94034,
                "name": "discharge",
                "description": None,
                "pipelineState": "STARTED",
                "pipelineStateMessage": None,
                "preconfigured": True,
                "scaleOuted": False,
            },
            "errorMessages": [],
        },
    )

    response = client._get_pipeline_info("LoadTesting", "discharge")

    assert response["id"] == 94034
    assert response["name"] == "discharge"
    assert response["description"] is None
    assert response["pipelineState"] == "STARTED"
    assert response["pipelineStateMessage"] is None
    assert response["preconfigured"] is True
    assert response["scaleOuted"] is False


def test_get_pipeline_configuration(client, requests_mock):
    requests_mock.get(
        f"{API_BASE}/textanalysis/projects/LoadTesting/pipelines/discharge/configuration",
        headers={"Content-Type": "application/json"},
        json={
            "payload": {
                "schemaVersion": "1.3",
                "name": "discharge",
                "description": None,
                "analysisEnginePoolSize": 1,
                "casPoolSize": 2,
                # ... truncated ...
            },
            "errorMessages": [],
        },
    )

    response = client._get_pipeline_configuration("LoadTesting", "discharge")

    assert response["name"] == "discharge"
    assert response["description"] is None
    assert response["analysisEnginePoolSize"] == 1
    assert response["casPoolSize"] == 2


def test_set_pipeline_configuration(client, requests_mock):
    requests_mock.put(
        f"{API_BASE}/textanalysis/projects/LoadTesting/pipelines/discharge/configuration",
        headers={"Content-Type": "application/json"},
        json={"payload": None, "errorMessages": []},
    )

    configuration = {
        "schemaVersion": "1.3",
        "name": "discharge",
        "description": None,
        "analysisEnginePoolSize": 1,
        "casPoolSize": 2,
        # ... truncated...
    }

    client._set_pipeline_configuration("LoadTesting", "discharge", configuration)


def test_create_document_collection(client, requests_mock):
    requests_mock.post(
        f"{API_BASE}/importer/projects/LoadTesting/documentCollections",
        headers={"Content-Type": "application/json"},
        json={
            "payload": {"name": "collection0"},
            "errorMessages": [],
        },
    )
    response = client._create_document_collection("LoadTesting", "collection0")
    assert response.name == "collection0"


def test_list_document_collections(client, requests_mock):
    requests_mock.get(
        f"{API_BASE}/importer/projects/LoadTesting/documentCollections",
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
    response = client._list_document_collections("LoadTesting")

    assert response[1]["name"] == "collection1"


def test_get_documents_collection(client, requests_mock):
    project = client.get_project("LoadTesting")
    requests_mock.get(
        f"{API_BASE}/importer/projects/LoadTesting/documentCollections/collection0",
        headers={"Content-Type": "application/json"},
        json={
            "payload": {"name": "collection0", "numberOfDocuments": 5},
            "errorMessages": [],
        },
    )
    response = client._get_document_collection(project.name, "collection0")
    assert response["numberOfDocuments"] == 5


def test_delete_document_collection(client, requests_mock):
    project = client.get_project("LoadTesting")
    requests_mock.delete(
        f"{API_BASE}/importer/projects/LoadTesting/documentCollections/collection0",
        json={
            "payload": {},
            "errorMessages": [],
        },
    )
    client._delete_document_collection(project.name, "collection0")


def test_import_txt_into_collection(client, requests_mock):
    project = client.get_project("LoadTesting")
    requests_mock.post(
        f"{API_BASE}/importer/projects/LoadTesting/documentCollections/collection0/documents",
        json={
            "payload": {"original_document_name": "text1.txt", "document_name": "text1.txt"},
            "errorMessages": [],
        },
    )
    file_path = os.path.join(TEST_DIRECTORY, "resources/texts/text1.txt")
    with open(file_path, "r", encoding="UTF-8") as input_io:
        response = client._import_documents(
            project.name, "collection0", input_io, mime_type="text/plain"
        )
    assert response[0]["original_document_name"] == "text1.txt"


def test_import_solr_xml_into_collection(client, requests_mock):
    project = client.get_project("LoadTesting")
    requests_mock.post(
        f"{API_BASE}/importer/projects/LoadTesting/documentCollections/collection0/documents",
        json={
            "payload": {
                "original_document_name": "disease_solr.xml",
                "document_name": "disease_solr.xml",
            },
            "errorMessages": [],
        },
    )
    file_path = os.path.join(TEST_DIRECTORY, "resources/xml/disease_solr.xml")
    with open(file_path, "r", encoding="UTF-8") as input_io:
        response = client._import_documents(
            project.name, "collection0", input_io, mime_type="application/vnd.averbis.solr+xml"
        )

    assert response[0]["original_document_name"] == "disease_solr.xml"

    # Otherwise, we get a ValueError
    with pytest.raises(Exception):
        client._import_documents(
            Path("dummy"), mime_type="application/vnd.averbis.solr+xml", filename="Dummy.txt"
        )


def test_list_terminologies(client, requests_mock):
    requests_mock.get(
        f"{API_BASE}/terminology/projects/LoadTesting/terminologies",
        headers={"Content-Type": "application/json"},
        json={
            "payload": [
                {
                    "terminologyName": "Test",
                    "label": "asdf",
                    "version": "",
                    "allowedLanguageCodes": ["en"],
                    "hierarchical": True,
                    "conceptType": "de.averbis.extraction.types.Concept",
                }
            ],
            "errorMessages": [],
        },
    )

    response = client._list_terminologies("LoadTesting")

    assert response[0]["terminologyName"] == "Test"


def test_create_terminology(client, requests_mock):
    requests_mock.post(
        f"{API_BASE}/terminology/projects/LoadTesting/terminologies",
        headers={"Content-Type": "application/json"},
        json={
            "payload": {
                "terminologyName": "term1",
                "label": "someLabel",
                "version": "1.0",
                "allowedLanguageCodes": ["de"],
                "hierarchical": True,
                "conceptType": "de.averbis.extraction.types.Concept",
            },
            "errorMessages": [],
        },
    )

    terminology = client._create_terminology(
        "LoadTesting", "term1", "someLabel", ["de"], version="1.0"
    )

    assert terminology["terminologyName"] == "term1"
    assert terminology["label"] == "someLabel"
    assert terminology["version"] == "1.0"
    assert terminology["hierarchical"] is True
    assert terminology["conceptType"] == "de.averbis.extraction.types.Concept"


def test_delete_terminology(client, requests_mock):
    requests_mock.request(
        "delete",
        f"{API_BASE}/terminology/projects/LoadTesting/terminologies/term1",
        json={"payload": None, "errorMessages": []},
    )

    client._delete_terminology("LoadTesting", "term1")


def test_start_terminology_export(client, requests_mock):
    requests_mock.request(
        "post",
        f"{API_BASE}/terminology/projects/LoadTesting/terminologies/term1/terminologyExports",
        json={
            "payload": None,
            "errorMessages": [],
        },
    )

    client._start_terminology_export("LoadTesting", "term1", TERMINOLOGY_EXPORTER_OBO_1_4)


def test_get_terminology_export_info(client, requests_mock):
    requests_mock.request(
        "get",
        f"{API_BASE}/terminology/projects/LoadTesting/terminologies/term1/terminologyExports",
        headers={"Content-Type": "application/json"},
        json={
            "payload": {
                "id": 19516,
                "terminologyId": 19515,
                "state": "PREPARING",
                "totalNumberOfConcepts": None,
                "numberOfProcessedConcepts": None,
                "startDate": 1596093621445,
                "endDate": None,
                "messageDtos": [],
                "exporterName": "Obo 1.4 Exporter",
                "stateMessage": "Preparing OBO download",
                "oboDownloadAvailable": False,
            },
            "errorMessages": [],
        },
    )

    response = client._get_terminology_export_info("LoadTesting", "term1")

    assert response["state"] == "PREPARING"


def test_start_terminology_import(client, requests_mock):
    requests_mock.request(
        "post",
        f"{API_BASE}/terminology/projects/LoadTesting/terminologies/term1/terminologyImports",
        headers={"Content-Type": "application/json"},
        json={
            "payload": None,
            "errorMessages": [],
        },
    )

    client._start_terminology_import("LoadTesting", "term1", TERMINOLOGY_IMPORTER_OBO, "<no data/>")


def test_get_terminology_import_info(client, requests_mock):
    requests_mock.request(
        "get",
        f"{API_BASE}/terminology/projects/LoadTesting/terminologies/term1/terminologyImports",
        headers={"Content-Type": "application/json"},
        json={
            "payload": {
                "id": 19524,
                "terminologyId": 19523,
                "state": "COMPLETED",
                "totalNumberOfConcepts": 769,
                "numberOfProcessedConcepts": 545,
                "numberOfSkippedConcepts": 224,
                "numberOfProcessedConceptsWithRelations": 769,
                "startDate": 1596101512218,
                "endDate": 1596101518642,
                "messageDtos": [
                    {"message": "Skipped concept [100000156089]: no terms given!"},
                    {"message": "Skipped concept [200000002082]: no terms given!"},
                    # ... truncated ...
                ],
            },
            "errorMessages": [],
        },
    )

    response = client._get_terminology_import_info("LoadTesting", "term1")

    assert response["state"] == "COMPLETED"


def test_analyse_text(client, requests_mock):
    requests_mock.post(
        f"{API_BASE}/textanalysis/projects/LoadTesting/pipelines/discharge/analyseText",
        headers={"Content-Type": "application/json"},
        json={
            "payload": [
                {
                    "begin": 28,
                    "end": 40,
                    "type": "de.averbis.types.health.Diagnosis",
                    "coveredText": "Appendizitis"
                    # ... truncated ...
                },
                {
                    "begin": 28,
                    "end": 40,
                    "type": "de.averbis.textanalysis.types.health.Diagnosis",
                    "coveredText": "Appendizitis"
                    # ... truncated ...
                },
            ],
            "errorMessages": [],
        },
    )

    response = client._analyse_text(
        "LoadTesting", "discharge", "Der Patient leidet an einer Appendizitis.", language="de"
    )

    assert response[0]["coveredText"] == "Appendizitis"


def test_analyse_texts_with_some_working_and_some_failing(client_version_5, requests_mock):
    requests_mock.get(
        f"{API_BASE}/textanalysis/projects/LoadTesting/pipelines/discharge/configuration",
        headers={"Content-Type": "application/json"},
        json={
            "payload": {"analysisEnginePoolSize": 4},
            "errorMessages": [],
        },
    )

    def callback(request, _):
        doc_text = request.text.read().decode("utf-8")
        if doc_text == "works":
            return {
                "payload": [
                    {
                        "begin": 0,
                        "end": len(doc_text),
                        "type": "uima.tcas.DocumentAnnotation",
                        "coveredText": doc_text
                        # ... truncated ...
                    },
                ],
                "errorMessages": [],
            }
        else:
            return {
                "payload": [],
                "errorMessages": ["Kaputt!"],
            }

    requests_mock.post(
        f"{API_BASE}/textanalysis/projects/LoadTesting/pipelines/discharge/analyseText",
        headers={"Content-Type": "application/json"},
        json=callback,
    )

    pipeline = Pipeline(Project(client_version_5, "LoadTesting"), "discharge")
    results = list(pipeline.analyse_texts(["works", "fails"]))

    assert results[0].successful() is True
    assert results[1].successful() is False


def test_analyse_html(client, requests_mock):
    requests_mock.post(
        f"{API_BASE}/textanalysis/projects/LoadTesting/pipelines/discharge/analyseHtml",
        headers={"Content-Type": "application/json"},
        json={
            "payload": [
                {
                    "begin": 28,
                    "end": 40,
                    "type": "de.averbis.types.health.Diagnosis",
                    "coveredText": "Appendizitis",
                    # ... truncated ...
                },
                {
                    "begin": 0,
                    "end": 41,
                    "type": "de.averbis.types.health.PatientInformation",
                    "coveredText": "Der Patient leidet an einer Appendizitis.",
                    # ... truncated ...
                },
                # ... truncated ...
            ],
            "errorMessages": [],
        },
    )

    response = client._analyse_html(
        "LoadTesting",
        "discharge",
        "<html><body>Der Patient leidet an einer Appendizitis.</body></html>",
        language="de",
    )

    assert response[0]["coveredText"] == "Appendizitis"


def test_classify_document(client, requests_mock):
    requests_mock.post(
        f"{API_BASE}/classification/projects/LoadTesting/classificationSets/Default/classifyDocument",
        headers={"Content-Type": "application/json"},
        json={
            "payload": {
                "classifications": [
                    {
                        "documentIdentifier": "UNKNOWN",
                        "success": True,
                        "labels": [{"confidence": 0.536, "name": "Include"}],
                        "errors": [{"message": "Document has no 'title' field"}],
                    }
                ]
            },
            "errorMessages": [],
        },
    )

    response = client._classify_document(
        "LoadTesting", "This is a test.".encode(ENCODING_UTF_8), "Default", DOCUMENT_IMPORTER_TEXT
    )

    assert response["classifications"][0]["documentIdentifier"] == "UNKNOWN"


def test_select(client, requests_mock):
    requests_mock.get(
        f"{API_BASE}/search/projects/LoadTesting/select",
        headers={"Content-Type": "application/json"},
        json={
            "payload": {
                "solrResponse": {
                    "responseHeader": {"status": 0, "QTime": 1},
                    "response": {"numFound": 0, "start": 0, "docs": []},
                },
                "conceptMapping": {},
                "entityMapping": {},
            },
            "errorMessages": [],
        },
    )

    response = client._select("LoadTesting")

    assert "solrResponse" in response


def test_with_settings_file(requests_mock_hd6):
    client = Client(
        "localhost-hd",
        settings=os.path.join(TEST_DIRECTORY, "resources/settings/client-settings.json"),
    )

    assert client._url == "https://localhost:8080/health-discovery"
    assert client._api_token == "dummy-token"
    assert client._verify_ssl is False


def test_with_settings_file_with_defaults_hd(requests_mock_hd6):
    hd_client = Client(
        "localhost-hd",
        settings=os.path.join(
            TEST_DIRECTORY, "resources/settings/client-settings-with-defaults.json"
        ),
    )

    assert hd_client._url == "https://localhost:8080/health-discovery"
    assert hd_client._api_token == "dummy-token"
    assert hd_client._verify_ssl == "caRoot.pem"


def test_with_settings_file_with_defaults_id(requests_mock_id6):
    id_client = Client(
        "localhost-id",
        settings=os.path.join(
            TEST_DIRECTORY, "resources/settings/client-settings-with-defaults.json"
        ),
    )

    assert id_client._url == "https://localhost:8080/information-discovery"
    assert id_client._api_token == "dummy-token"
    assert id_client._verify_ssl == "id.pem"
