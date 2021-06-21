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

from averbis import DocumentCollection
from tests.fixtures import *


@pytest.fixture()
def document_collection(client) -> DocumentCollection:
    project = client.get_project("LoadTesting")
    return DocumentCollection(project, "my_collection")


def test_infer_mime_type_for_plain_text(document_collection, requests_mock):
    requests_mock.post(
        f"{API_BASE}/importer/projects/LoadTesting/documentCollections/my_collection/documents",
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


def test_infer_mime_type_for_solr_xml(client, requests_mock):
    project = client.get_project("LoadTesting")
    document_collection = DocumentCollection(project, "my_collection")
    requests_mock.post(
        f"{API_BASE}/importer/projects/LoadTesting/documentCollections/my_collection/documents",
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


def test_list_document_collection(client, requests_mock):
    project = client.get_project("LoadTesting")
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

    collections = project.list_document_collections()

    assert collections[2].name == "collection2"


def test_export_analysis_results(client, requests_mock):

    project = client.get_project("LoadTesting")
    collection = project.get_document_collection("my-collection")
    document_id = "document0001"
    process_name = "my-process"
    expected_xmi = '<?xml version="1.0" encoding="UTF-8"?><xmi:XMI/>'

    requests_mock.get(
        f"{API_EXPERIMENTAL}/textanalysis/projects/{project.name}/documentCollections/{collection.name}"
        f"/documents/{document_id}/processes/{process_name}/exportTextAnalysisResult",
        headers={"Content-Type": "application/vnd.uima.cas+xmi"},
        text=expected_xmi,
    )

    xmi = collection.export_analysis_results(document_id, process_name)

    assert xmi == expected_xmi
