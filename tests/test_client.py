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
import zipfile
import tempfile
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


def test_build_url(client):
    client._url = "http://some-machine/health-discovery/"
    assert (
        client._build_url("v1/some-endpoint/")
        == "http://some-machine/health-discovery/rest/v1/some-endpoint/"
    )


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

    project = client.create_project(PROJECT_NAME, "Project for load testing")

    assert project.name == PROJECT_NAME


def test_get_project(client):
    project = client.get_project(PROJECT_NAME)

    assert project.name == PROJECT_NAME


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


def test_exists_project(client, requests_mock):
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

    assert client.exists_project("Jumble") is True
    assert client.exists_project("Bumble") is True
    assert client.exists_project("Mumble") is False


def test_delete_project(client_version_5):
    with pytest.raises(OperationNotSupported):
        client._delete_project(PROJECT_NAME)


def test_delete_project(client_version_6, requests_mock):
    project = client_version_6.get_project(PROJECT_NAME)
    requests_mock.delete(
        f"{API_EXPERIMENTAL}/projects/{project.name}",
        headers={"Content-Type": "application/json"},
        json={"payload": None, "errorMessages": []},
    )
    response = project.delete()

    assert response is None


def test_create_pipeline(client, requests_mock):
    requests_mock.post(
        f"{API_BASE}/textanalysis/projects/{PROJECT_NAME}/pipelines",
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

    new_pipeline = client._create_pipeline(PROJECT_NAME, configuration)

    assert new_pipeline is None


def test_create_pipeline_schema_version_two(client, requests_mock):
    requests_mock.post(
        f"{API_BASE}/textanalysis/projects/{PROJECT_NAME}/pipelines",
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

    new_pipeline = client._create_pipeline(PROJECT_NAME, configuration)

    assert new_pipeline is None


def test_start_pipeline(client, requests_mock):
    requests_mock.put(
        f"{API_BASE}/textanalysis/projects/{PROJECT_NAME}/pipelines/discharge/start",
        headers={"Content-Type": "application/json"},
        json={"payload": None, "errorMessages": []},
    )

    response = client._start_pipeline(PROJECT_NAME, "discharge")

    assert response is None


def test_stop_pipeline(client, requests_mock):
    requests_mock.put(
        f"{API_BASE}/textanalysis/projects/{PROJECT_NAME}/pipelines/discharge/stop",
        headers={"Content-Type": "application/json"},
        json={"payload": None, "errorMessages": []},
    )

    response = client._stop_pipeline(PROJECT_NAME, "discharge")

    assert response is None


def test_get_pipeline_info(client, requests_mock):
    requests_mock.get(
        f"{API_BASE}/textanalysis/projects/{PROJECT_NAME}/pipelines/discharge",
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

    response = client._get_pipeline_info(PROJECT_NAME, "discharge")

    assert response["id"] == 94034
    assert response["name"] == "discharge"
    assert response["description"] is None
    assert response["pipelineState"] == "STARTED"
    assert response["pipelineStateMessage"] is None
    assert response["preconfigured"] is True
    assert response["scaleOuted"] is False


def test_get_pipeline_configuration(client, requests_mock):
    requests_mock.get(
        f"{API_BASE}/textanalysis/projects/{PROJECT_NAME}/pipelines/discharge/configuration",
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

    response = client._get_pipeline_configuration(PROJECT_NAME, "discharge")

    assert response["name"] == "discharge"
    assert response["description"] is None
    assert response["analysisEnginePoolSize"] == 1
    assert response["casPoolSize"] == 2


def test_set_pipeline_configuration(client, requests_mock):
    requests_mock.put(
        f"{API_BASE}/textanalysis/projects/{PROJECT_NAME}/pipelines/discharge/configuration",
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

    client._set_pipeline_configuration(PROJECT_NAME, "discharge", configuration)


def test_create_document_collection(client, requests_mock):
    requests_mock.post(
        f"{API_BASE}/importer/projects/{PROJECT_NAME}/documentCollections",
        headers={"Content-Type": "application/json"},
        json={
            "payload": {"name": "collection0"},
            "errorMessages": [],
        },
    )
    response = client._create_document_collection(PROJECT_NAME, "collection0")
    assert response.name == "collection0"


def test_list_document_collections(client, requests_mock):
    requests_mock.get(
        f"{API_BASE}/importer/projects/{PROJECT_NAME}/documentCollections",
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
    response = client._list_document_collections(PROJECT_NAME)

    assert response[1]["name"] == "collection1"


def test_get_documents_collection(client, requests_mock):
    project = client.get_project(PROJECT_NAME)
    requests_mock.get(
        f"{API_BASE}/importer/projects/{PROJECT_NAME}/documentCollections/collection0",
        headers={"Content-Type": "application/json"},
        json={
            "payload": {"name": "collection0", "numberOfDocuments": 5},
            "errorMessages": [],
        },
    )
    response = client._get_document_collection(project.name, "collection0")
    assert response["numberOfDocuments"] == 5


def test_delete_document_collection(client, requests_mock):
    project = client.get_project(PROJECT_NAME)
    requests_mock.delete(
        f"{API_BASE}/importer/projects/{PROJECT_NAME}/documentCollections/collection0",
        json={
            "payload": {},
            "errorMessages": [],
        },
    )
    client._delete_document_collection(project.name, "collection0")


def test_import_txt_into_collection(client, requests_mock):
    project = client.get_project(PROJECT_NAME)
    requests_mock.post(
        f"{API_BASE}/importer/projects/{PROJECT_NAME}/documentCollections/collection0/documents",
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
    project = client.get_project(PROJECT_NAME)
    requests_mock.post(
        f"{API_BASE}/importer/projects/{PROJECT_NAME}/documentCollections/collection0/documents",
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
        f"{API_BASE}/terminology/projects/{PROJECT_NAME}/terminologies",
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

    response = client._list_terminologies(PROJECT_NAME)

    assert response[0]["terminologyName"] == "Test"


def test_create_terminology(client, requests_mock):
    requests_mock.post(
        f"{API_BASE}/terminology/projects/{PROJECT_NAME}/terminologies",
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
        PROJECT_NAME, "term1", "someLabel", ["de"], version="1.0"
    )

    assert terminology["terminologyName"] == "term1"
    assert terminology["label"] == "someLabel"
    assert terminology["version"] == "1.0"
    assert terminology["hierarchical"] is True
    assert terminology["conceptType"] == "de.averbis.extraction.types.Concept"


def test_delete_terminology(client, requests_mock):
    requests_mock.request(
        "delete",
        f"{API_BASE}/terminology/projects/{PROJECT_NAME}/terminologies/term1",
        json={"payload": None, "errorMessages": []},
    )

    client._delete_terminology(PROJECT_NAME, "term1")


def test_start_terminology_export(client, requests_mock):
    requests_mock.request(
        "post",
        f"{API_BASE}/terminology/projects/{PROJECT_NAME}/terminologies/term1/terminologyExports",
        json={
            "payload": None,
            "errorMessages": [],
        },
    )

    client._start_terminology_export(PROJECT_NAME, "term1", TERMINOLOGY_EXPORTER_OBO_1_4)


def test_get_terminology_export_info(client, requests_mock):
    requests_mock.request(
        "get",
        f"{API_BASE}/terminology/projects/{PROJECT_NAME}/terminologies/term1/terminologyExports",
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

    response = client._get_terminology_export_info(PROJECT_NAME, "term1")

    assert response["state"] == "PREPARING"


def test_start_terminology_import(client, requests_mock):
    requests_mock.request(
        "post",
        f"{API_BASE}/terminology/projects/{PROJECT_NAME}/terminologies/term1/terminologyImports",
        headers={"Content-Type": "application/json"},
        json={
            "payload": None,
            "errorMessages": [],
        },
    )

    client._start_terminology_import(PROJECT_NAME, "term1", TERMINOLOGY_IMPORTER_OBO, "<no data/>")


def test_get_terminology_import_info(client, requests_mock):
    requests_mock.request(
        "get",
        f"{API_BASE}/terminology/projects/{PROJECT_NAME}/terminologies/term1/terminologyImports",
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

    response = client._get_terminology_import_info(PROJECT_NAME, "term1")

    assert response["state"] == "COMPLETED"


def test_analyse_text(client, requests_mock):
    requests_mock.post(
        f"{API_BASE}/textanalysis/projects/{PROJECT_NAME}/pipelines/discharge/analyseText",
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
        PROJECT_NAME, "discharge", "Der Patient leidet an einer Appendizitis.", language="de"
    )

    assert response[0]["coveredText"] == "Appendizitis"


def test_analyse_texts_with_some_working_and_some_failing(client_version_5, requests_mock):
    requests_mock.get(
        f"{API_BASE}/textanalysis/projects/{PROJECT_NAME}/pipelines/discharge/configuration",
        headers={"Content-Type": "application/json"},
        json={
            "payload": {"analysisEnginePoolSize": 4},
            "errorMessages": [],
        },
    )

    def callback(request, context):
        doc_text = request.text.read().decode("utf-8")
        if doc_text == "works":
            context.status_code = 200
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
            context.status_code = 500
            return {
                "payload": [],
                "errorMessages": ["Kaputt!"],
            }

    requests_mock.post(
        f"{API_BASE}/textanalysis/projects/{PROJECT_NAME}/pipelines/discharge/analyseText",
        headers={"Content-Type": "application/json"},
        json=callback,
    )

    pipeline = Pipeline(Project(client_version_5, PROJECT_NAME), "discharge")
    results = list(pipeline.analyse_texts(["works", "fails"]))

    assert results[0].successful() is True
    assert results[1].successful() is False


def test_analyse_html(client, requests_mock):
    requests_mock.post(
        f"{API_BASE}/textanalysis/projects/{PROJECT_NAME}/pipelines/discharge/analyseHtml",
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
        PROJECT_NAME,
        "discharge",
        "<html><body>Der Patient leidet an einer Appendizitis.</body></html>",
        language="de",
    )

    assert response[0]["coveredText"] == "Appendizitis"


def test_classify_document(client, requests_mock):
    requests_mock.post(
        f"{API_BASE}/classification/projects/{PROJECT_NAME}/classificationSets/Default/classifyDocument",
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
        PROJECT_NAME, "This is a test.".encode(ENCODING_UTF_8), "Default", DOCUMENT_IMPORTER_TEXT
    )

    assert response["classifications"][0]["documentIdentifier"] == "UNKNOWN"


def test_list_resources(client, requests_mock):
    expected_resources_list = [
        "test1.txt",
        "test2.txt",
        "test3.txt",
    ]

    requests_mock.get(
        f"{API_EXPERIMENTAL}/textanalysis/resources",
        headers={"Content-Type": "application/json"},
        json={"payload": {"files": expected_resources_list}, "errorMessages": []},
    )

    actual_resources_list = client.list_resources()
    assert actual_resources_list == expected_resources_list


def test_download_resources(client, requests_mock):
    target_path = Path(TEST_DIRECTORY) / "resources/download/zip_test.zip"
    try:
        os.remove(target_path)
    except OSError:
        pass

    example_text = "some text"
    requests_mock.get(
        f"{API_EXPERIMENTAL}/textanalysis/resources",
        headers={"Content-Type": "application/zip"},
        text=example_text,
    )

    client.download_resources(target_path)

    assert os.path.exists(target_path)
    assert example_text == target_path.read_text()

    os.remove(target_path)


def test_delete_resources(client, requests_mock):

    requests_mock.delete(
        f"{API_EXPERIMENTAL}/textanalysis" f"/resources",
        headers={"Content-Type": "application/json"},
        json={"payload": None, "errorMessages": []},
    )

    client.delete_resources()


def test_select(client, requests_mock):
    requests_mock.get(
        f"{API_BASE}/search/projects/{PROJECT_NAME}/select",
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

    response = client._select(PROJECT_NAME)

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


def test_handle_error_outside_platform(client, requests_mock):
    """Simulates an error that is outside the scope of our platform."""
    requests_mock.get(
        f"{API_BASE}/invalid_url",
        headers={"Content-Type": "application/json"},
        reason="Not found",
        status_code=404,
    )
    with pytest.raises(Exception) as ex:
        client._Client__request_with_json_response(method="get", endpoint=f"v1/invalid_url")
    expected_error_message = "404 Server Error: 'Not found' for url: 'https://localhost:8080/information-discovery/rest/v1/invalid_url'."
    assert str(ex.value) == expected_error_message


def test_handle_error_in_non_existing_endpoint(client, requests_mock):
    """Simulates the scenario that an invalid URL is called. The URL is in the namespace of a platform."""
    requests_mock.get(
        f"{API_BASE}/invalid_url",
        headers={"Content-Type": "application/json"},
        json={
            "servlet": "Platform",
            "message": "Not Found",
            "url": f"{API_BASE}/invalid_url",
        },
        status_code=404,
    )
    with pytest.raises(Exception) as ex:
        client._Client__request_with_json_response(method="get", endpoint="v1/invalid_url")
    expected_error_message = "404 Server Error: 'None' for url: 'https://localhost:8080/information-discovery/rest/v1/invalid_url'.\nPlatform error message is: 'Not Found'"
    assert str(ex.value) == expected_error_message


def test_handle_error_bad_request(client, requests_mock):
    """Simulates a bad request with error message 400, e.g. creating a project that already exists."""
    requests_mock.get(
        f"{API_BASE}/invalid_url",
        headers={"Content-Type": "application/json"},
        json={"payload": None, "errorMessages": ["A project with name 'test' already exists."]},
        status_code=400,
    )
    with pytest.raises(Exception) as ex:
        client._Client__request_with_json_response(method="get", endpoint="v1/invalid_url")
    expected_error_message = (
        "400 Server Error: 'None' for url: 'https://localhost:8080/information-discovery/rest/v1/invalid_url'.\n"
        "Endpoint error message is: 'A project with name 'test' already exists.'"
    )
    assert str(ex.value) == expected_error_message


def test_handle_error_no_access(client, requests_mock):
    """Simulates the scenario where the user has no access."""
    requests_mock.get(f"{API_BASE}/url/that/cannot/be/accessed", status_code=401)
    with pytest.raises(Exception) as ex:
        client._Client__request_with_json_response(
            method="get", endpoint="v1/url/that/cannot/be/accessed"
        )
    expected_error_message = "401 Server Error: 'None' for url: 'https://localhost:8080/information-discovery/rest/v1/url/that/cannot/be/accessed'."
    assert str(ex.value) == expected_error_message


def test_upload_resources(client_version_6, requests_mock):
    requests_mock.post(
        f"{API_EXPERIMENTAL}/textanalysis/resources",
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
    resources = client_version_6.upload_resources(
        Path(TEST_DIRECTORY) / "resources/zip_test/text1.txt"
    )
    assert len(resources) == 1


def test_create_zip_io__file_does_not_exist(client):
    with pytest.raises(Exception) as ex:
        client._create_zip_io("not-existing-file.txt")
    expected_error_message = "not-existing-file.txt does not exist."
    assert str(ex.value) == expected_error_message


def test_create_zip_io__zip_file_io(client):
    zip_archive_bytes_io = open(Path(TEST_DIRECTORY) / "resources/zip_test/zip_test.zip", "rb")
    zip_archive_bytes_io = client._create_zip_io(zip_archive_bytes_io)
    zip_file = zipfile.ZipFile(zip_archive_bytes_io)
    files_in_zip = [f.filename for f in zip_file.filelist]
    assert len(files_in_zip) == 5
    assert "text1.txt" in files_in_zip
    assert "text2.txt" in files_in_zip
    assert "text3.txt" in files_in_zip
    assert "sub/" in files_in_zip
    assert "sub/text4.txt" in files_in_zip


def test_create_zip_io__single_file(client):
    zip_archive_bytes_io = client._create_zip_io(
        TEST_DIRECTORY + "/" + "resources/zip_test/text1.txt"
    )
    zip_file = zipfile.ZipFile(zip_archive_bytes_io)
    files_in_zip = [f.filename for f in zip_file.filelist]
    assert len(files_in_zip) == 1
    assert "text1.txt" in files_in_zip


def test_create_zip_io__single_file_with_path_in_zip(client):
    zip_archive_bytes_io = client._create_zip_io(
        TEST_DIRECTORY + "/" + "resources/zip_test/text1.txt", path_in_zip="abc"
    )
    zip_file = zipfile.ZipFile(zip_archive_bytes_io)
    files_in_zip = [f.filename for f in zip_file.filelist]
    assert len(files_in_zip) == 1
    assert "abc/text1.txt" in files_in_zip


def test_create_zip_io__folder_with_path_in_zip(client):
    zip_archive_bytes_io = client._create_zip_io(
        TEST_DIRECTORY + "/" + "resources/zip_test", path_in_zip="abc"
    )
    assert_zip_archive_bytes_io_content(zip_archive_bytes_io, "abc/")


def test_create_zip_io__folder_as_path_with_path_in_zip(client):
    zip_archive_bytes_io = client._create_zip_io(
        Path(TEST_DIRECTORY) / "resources/zip_test", path_in_zip="abc"
    )
    assert_zip_archive_bytes_io_content(zip_archive_bytes_io, "abc/")


def test_create_zip_io__folder(client):
    zip_archive_bytes_io = client._create_zip_io(TEST_DIRECTORY + "/" + "resources/zip_test")
    assert_zip_archive_bytes_io_content(zip_archive_bytes_io)


def assert_zip_archive_bytes_io_content(zip_archive_bytes_io, prefix=""):
    zip_file = zipfile.ZipFile(zip_archive_bytes_io)
    files_in_zip = [f.filename for f in zip_file.filelist]
    assert len(files_in_zip) == 5
    assert f"{prefix}text2.txt" in files_in_zip
    assert f"{prefix}text1.txt" in files_in_zip
    assert f"{prefix}text3.txt" in files_in_zip
    assert f"{prefix}sub/text4.txt" in files_in_zip
    assert f"{prefix}zip_test.zip" in files_in_zip
