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

import pytest

from averbis import Project, Client

URL_BASE = "http://localhost:8080"
API_BASE = URL_BASE + "/rest/v1"

logging.basicConfig(level=logging.INFO)


@pytest.fixture
def project() -> Project:
    return Client(URL_BASE).get_project("LoadTesting")


def test_that_create_pipeline_accepts_name_override(project, requests_mock):
    requests_mock.post(
        f"{API_BASE}/textanalysis/projects/LoadTesting/pipelines",
        headers={"Content-Type": "application/json"},
        json={"payload": None, "errorMessages": []},
    )
    configuration = {"name": "discharge"}
    pipeline = project.create_pipeline(configuration, name="discharge2")

    assert pipeline.name == "discharge2"


def test_that_get_pipeline_returns_same_instance_on_consecutive_calls(project, requests_mock):
    pipeline1 = project.get_pipeline("discharge")
    pipeline2 = project.get_pipeline("discharge")

    assert pipeline1 is pipeline2
