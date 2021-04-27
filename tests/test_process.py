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
    project = client.get_project("LoadTesting")
    return Process(project, "my_process", "my_doc_source", "my_pipeline", "IDLE", 12)


def test_delete(process, requests_mock):

    requests_mock.delete(
        f"{API_EXPERIMENTAL}/textanalysis/projects/LoadTesting/documentSources/{process.document_source_name}/processes/{process.name}",
        headers={"Content-Type": "application/json"},
        json={"payload": None, "errorMessages": []},
    )

    process.delete()


def test_reprocess(process, requests_mock):

    requests_mock.post(
        f"{API_EXPERIMENTAL}/textanalysis/projects/LoadTesting/documentSources/{process.document_source_name}/processes/{process.name}/reprocess",
        headers={"Content-Type": "application/json"},
        json={"payload": None, "errorMessages": []},
    )

    process.reprocess()

