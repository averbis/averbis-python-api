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

"""Access to core functionalities of Averbis products"""

from ._rest_client import (
    OperationNotSupported,
    OperationTimeoutError,
    Terminology,
    Client,
    Result,
    Pipeline,
    Project,
    DocumentCollection,
    Pear,
    Process,
    DOCUMENT_IMPORTER_CAS,
    DOCUMENT_IMPORTER_SOLR,
    DOCUMENT_IMPORTER_TEXT,
    HEADER_CONTENT_TYPE,
    HEADER_ACCEPT,
    MEDIA_TYPE_ANY,
    MEDIA_TYPE_APPLICATION_JSON,
    MEDIA_TYPE_APPLICATION_XMI,
    MEDIA_TYPE_APPLICATION_SOLR_XML,
    MEDIA_TYPE_APPLICATION_XML,
    MEDIA_TYPE_OCTET_STREAM,
    MEDIA_TYPE_TEXT_PLAIN,
    MEDIA_TYPE_TEXT_PLAIN_UTF8,
    TERMINOLOGY_EXPORTER_CONCEPT_DICTIONARY_XML,
    TERMINOLOGY_EXPORTER_OBO_1_4,
    TERMINOLOGY_EXPORTER_SOLR_AUTO_SUGGEST_XML,
    TERMINOLOGY_IMPORTER_OBO,
    ENCODING_UTF_8,
)

__all__ = [
    "OperationNotSupported",
    "OperationTimeoutError",
    "Terminology",
    "Client",
    "Result",
    "Pipeline",
    "Project",
    "DocumentCollection",
    "Pear",
    "Process",
    "DOCUMENT_IMPORTER_CAS",
    "DOCUMENT_IMPORTER_SOLR",
    "DOCUMENT_IMPORTER_TEXT",
    "HEADER_CONTENT_TYPE",
    "HEADER_ACCEPT",
    "MEDIA_TYPE_ANY",
    "MEDIA_TYPE_APPLICATION_JSON",
    "MEDIA_TYPE_APPLICATION_XMI",
    "MEDIA_TYPE_APPLICATION_XML",
    "MEDIA_TYPE_APPLICATION_SOLR_XML",
    "MEDIA_TYPE_OCTET_STREAM",
    "MEDIA_TYPE_TEXT_PLAIN",
    "MEDIA_TYPE_TEXT_PLAIN_UTF8",
    "TERMINOLOGY_EXPORTER_CONCEPT_DICTIONARY_XML",
    "TERMINOLOGY_EXPORTER_OBO_1_4",
    "TERMINOLOGY_EXPORTER_SOLR_AUTO_SUGGEST_XML",
    "TERMINOLOGY_IMPORTER_OBO",
    "ENCODING_UTF_8",
]
