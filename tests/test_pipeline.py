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
import time
from pathlib import Path

from averbis import Project, Pipeline, Process
from averbis.core import OperationTimeoutError, OperationNotSupported
from tests.fixtures import *

logging.basicConfig(level=logging.INFO)


@pytest.fixture
def pipeline_endpoint_behavior_mock():
    return PipelineEndpointMock()


@pytest.fixture(autouse=True)
def pipeline_requests_mock(pipeline_endpoint_behavior_mock, requests_mock):
    requests_mock.get(
        f"{API_BASE}/textanalysis/projects/LoadTesting/pipelines/discharge",
        headers={"Content-Type": "application/json"},
        json=pipeline_endpoint_behavior_mock.info_callback,
    )
    requests_mock.put(
        f"{API_BASE}/textanalysis/projects/LoadTesting/pipelines/discharge/start",
        headers={"Content-Type": "application/json"},
        json=pipeline_endpoint_behavior_mock.start_callback,
    )
    requests_mock.put(
        f"{API_BASE}/textanalysis/projects/LoadTesting/pipelines/discharge/stop",
        headers={"Content-Type": "application/json"},
        json=pipeline_endpoint_behavior_mock.stop_callback,
    )


@pytest.fixture
def pipeline_analyse_text_mock(client, requests_mock):
    # In the pipeline configuration, the name for the number of instances differs between platform version 5 and 6.
    if client.get_spec_version().startswith("5."):
        payload = {"analysisEnginePoolSize": 4}
    else:
        payload = {"numberOfInstances": 4}

    requests_mock.get(
        f"{API_BASE}/textanalysis/projects/LoadTesting/pipelines/discharge/configuration",
        headers={"Content-Type": "application/json"},
        json={
            "payload": payload,
            "errorMessages": [],
        },
    )

    def callback(request, _content):
        doc_text = request.text.read().decode("utf-8")
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

    requests_mock.post(
        f"{API_BASE}/textanalysis/projects/LoadTesting/pipelines/discharge/analyseText",
        headers={"Content-Type": "application/json"},
        json=callback,
    )


def test_ensure_started(client, pipeline_endpoint_behavior_mock):
    pipeline_endpoint_behavior_mock.set_state(Pipeline.STATE_STOPPED)

    pipeline = client.get_project("LoadTesting").get_pipeline("discharge")
    pipeline.pipeline_state_change_timeout = 3
    pipeline.pipeline_state_poll_interval = 1

    assert pipeline.is_started() is False
    pipeline.ensure_started()
    assert pipeline.is_started() is True


def test_ensure_stopped(client, pipeline_endpoint_behavior_mock):
    pipeline_endpoint_behavior_mock.set_state(Pipeline.STATE_STARTED)

    pipeline = client.get_project("LoadTesting").get_pipeline("discharge")
    pipeline.pipeline_state_change_timeout = 3
    pipeline.pipeline_state_poll_interval = 1

    assert pipeline.is_started() is True
    pipeline.ensure_stopped()
    assert pipeline.is_started() is False


def test_ensure_started_timeout(client, pipeline_endpoint_behavior_mock):
    pipeline_endpoint_behavior_mock.set_state(Pipeline.STATE_STOPPED, locked=True)

    pipeline = client.get_project("LoadTesting").get_pipeline("discharge")
    pipeline.pipeline_state_change_timeout = 2
    pipeline.pipeline_state_poll_interval = 1

    assert pipeline.is_started() is False

    with pytest.raises(OperationTimeoutError):
        pipeline.ensure_started()


def test_ensure_started_failure_to_start(client, pipeline_endpoint_behavior_mock):
    error_message = "Starting failed: org.apache.uima.ruta.extensions.RutaParseRuntimeException"

    pipeline_endpoint_behavior_mock.set_state(
        Pipeline.STATE_STOPPED,
        locked=True,
        pipeline_state_message=error_message,
    )

    pipeline = client.get_project("LoadTesting").get_pipeline("discharge")
    pipeline.pipeline_state_change_timeout = 2
    pipeline.pipeline_state_poll_interval = 1

    assert pipeline.is_started() is False

    with pytest.raises(Exception) as ex:
        pipeline.ensure_started()

    assert error_message in str(ex.value)


class PipelineEndpointMock:
    def __init__(self):
        self.change_state_after = 1
        self.last_state_change_request = time.time()
        self.state = Pipeline.STATE_STOPPED
        self.pipeline_state_message = None
        self.requested_state = Pipeline.STATE_STOPPED
        self.requested_state_pipeline_state_message = None
        self.state_locked = False

    def set_state(
        self, state: str, locked: bool = False, pipeline_state_message: str = None
    ) -> None:
        self.state = state
        self.requested_state = state
        self.state_locked = locked
        self.requested_state_pipeline_state_message = pipeline_state_message

    def info_callback(self, _request, _content):
        if (
            not self.state_locked
            and self.last_state_change_request + self.change_state_after < time.time()
        ):
            self.state = self.requested_state

        if self.last_state_change_request + self.change_state_after < time.time():
            self.pipeline_state_message = self.requested_state_pipeline_state_message

        return {
            "payload": {
                "id": 94034,
                "name": "discharge",
                "description": None,
                "pipelineState": self.state,
                "pipelineStateMessage": self.pipeline_state_message,
                "preconfigured": True,
                "scaleOuted": False,
            },
            "errorMessages": [],
        }

    def start_callback(self, _request, _content):
        self.last_state_change_request = time.time()
        self.requested_state = Pipeline.STATE_STARTED
        return {"payload": {}, "errorMessages": []}

    def stop_callback(self, _request, _content):
        self.last_state_change_request = time.time()
        self.requested_state = Pipeline.STATE_STOPPED
        return {"payload": {}, "errorMessages": []}


def test_analyse_texts_with_paths(client, pipeline_analyse_text_mock):
    pipeline = Pipeline(Project(client, "LoadTesting"), "discharge")

    results = pipeline.analyse_texts(Path("tests/resources/texts").glob("*.txt"))

    expected_results = []
    for input_file in Path("tests/resources/texts").glob("*.txt"):
        with open(input_file, "r", encoding="UTF-8") as input_io:
            expected_results.append(
                {"source": str(input_file).replace(os.sep, "/"), "text": input_io.read()}
            )

    assert [
        {"source": result.source.replace(os.sep, "/"), "text": result.data[0]["coveredText"]}
        for result in sorted(results, key=lambda x: x.source)
    ] == sorted(expected_results, key=lambda x: x["source"])


def test_analyse_texts_with_files(client, pipeline_analyse_text_mock):
    pipeline = Pipeline(Project(client, "LoadTesting"), "discharge")
    file1_path = os.path.join(TEST_DIRECTORY, "resources/texts/text1.txt")
    file2_path = os.path.join(TEST_DIRECTORY, "resources/texts/text2.txt")

    with open(file1_path, "rb") as file1, open(file2_path, "rb") as file2:
        results = pipeline.analyse_texts([file1, file2])
        sources = [result.source.replace(os.sep, "/") for result in results]

    assert sources[0].endswith("tests/resources/texts/text1.txt")
    assert sources[1].endswith("tests/resources/texts/text2.txt")


def test_analyse_texts_(client, pipeline_analyse_text_mock):
    pipeline = Pipeline(Project(client, "LoadTesting"), "discharge")
    file1_path = os.path.join(TEST_DIRECTORY, "resources/texts/text1.txt")
    file2_path = os.path.join(TEST_DIRECTORY, "resources/texts/text2.txt")

    with open(file1_path, "rb") as file1, open(file2_path, "rb") as file2:
        results = pipeline.analyse_texts([file1, file2])
        sources = [result.source.replace(os.sep, "/") for result in results]

    assert sources[0].endswith("tests/resources/texts/text1.txt")
    assert sources[1].endswith("tests/resources/texts/text2.txt")


def test_delete_pipeline_v5(client_version_5):
    pipeline = Pipeline(Project(client_version_5, "LoadTesting"), "discharge")
    with pytest.raises(OperationNotSupported):
        pipeline.delete()


def test_delete_pipeline_v6(client_version_6, requests_mock):
    pipeline = Pipeline(Project(client_version_6, "LoadTesting"), "discharge")
    requests_mock.delete(
        f"{URL_BASE_ID}/rest/experimental/textanalysis/projects/LoadTesting/pipelines/discharge",
        headers={"Content-Type": "application/json"},
        json={"payload": None, "errorMessages": []},
    )
    pipeline.delete()


def test_collection_process_complete(client_version_6, requests_mock):
    pipeline = Pipeline(Project(client_version_6, "LoadTesting"), "discharge")
    requests_mock.post(
        f"{URL_BASE_ID}/rest/experimental/textanalysis/projects/"
        f"LoadTesting/pipelines/discharge/collectionProcessComplete",
        headers={"Content-Type": "application/json"},
        json={"payload": None, "errorMessages": []},
        status_code=204
    )
    pipeline.collection_process_complete()
