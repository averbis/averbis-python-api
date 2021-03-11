#
# Copyright (c) 2020 Averbis GmbH.
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

from tests.fixtures import *

logging.basicConfig(level=logging.INFO)


def test_that_create_pipeline_accepts_name_override(client_version_5, requests_mock):
    project = client_version_5.get_project("LoadTesting")
    requests_mock.post(
        f"{API_BASE}/textanalysis/projects/LoadTesting/pipelines",
        headers={"Content-Type": "application/json"},
        json={"payload": None, "errorMessages": []},
    )
    configuration = {"pipelineName": "discharge", "schemaVersion": "1.3"}
    pipeline = project.create_pipeline(configuration, name="discharge2")

    assert pipeline.name == "discharge2"


def test_that_create_pipeline_schema_1(client_version_5, requests_mock):
    # The pipeline name parameter is "name" in version 5 and "pipelineName" in version 6
    project = client_version_5.get_project("LoadTesting")
    requests_mock.post(
        f"{API_BASE}/textanalysis/projects/LoadTesting/pipelines",
        headers={"Content-Type": "application/json"},
        json={"payload": None, "errorMessages": []},
    )
    configuration = {"name": "discharge-new", "schemaVersion": "1.3"}
    pipeline = project.create_pipeline(configuration)

    assert pipeline.name == "discharge-new"


def test_that_create_pipeline_schema_2(client_version_6, requests_mock):
    # The pipeline name parameter is "name" in version 5 and "pipelineName" in version 6
    project = client_version_6.get_project("LoadTesting")
    requests_mock.post(
        f"{API_BASE}/textanalysis/projects/LoadTesting/pipelines",
        headers={"Content-Type": "application/json"},
        json={"payload": None, "errorMessages": []},
    )
    configuration = {"pipelineName": "discharge-new", "schemaVersion": "2.0"}
    pipeline = project.create_pipeline(configuration)

    assert pipeline.name == "discharge-new"


def test_that_get_pipeline_returns_same_instance_on_consecutive_calls(client):
    project = client.get_project("LoadTesting")
    pipeline1 = project.get_pipeline("discharge")
    pipeline2 = project.get_pipeline("discharge")

    assert pipeline1 is pipeline2
