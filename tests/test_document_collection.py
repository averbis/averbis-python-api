from averbis import DocumentCollection
from fixtures import *


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
        document_collection.import_documents(input_io)


def test_infer_mime_type_for_solr_xml(client, requests_mock):
    project = client.get_project("LoadTesting")
    document_collection = DocumentCollection(project, "my_collection")
    requests_mock.post(
        f"{API_BASE}/importer/projects/LoadTesting/documentCollections/my_collection/documents",
        json={
            "payload": {
                "original_document_name": "disease_solr.xml",
                "document_name": "disease_solr.xml",
            },
            "errorMessages": [],
        },
    )
    file_path_xml = os.path.join(TEST_DIRECTORY, "resources/xml/disease_solr.xml")
    with open(file_path_xml, "r", encoding="UTF-8") as input_io:
        # Please note that it only works for solr-xml, if we explicitly set the mime-type
        document_collection.import_documents(input_io, mime_type="application/vnd.averbis.solr+xml")

        # Otherwise, we get a ValueError
        with pytest.raises(ValueError):
            document_collection.import_documents(input_io)


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
