#
# Copyright (c) 2024 Averbis GmbH.
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
import os
from pathlib import Path

from averbis import ResourceContainer
from tests.fixtures import *

TEST_DIRECTORY = os.path.dirname(__file__)

logging.basicConfig(level=logging.INFO)


def test_list_resources(client, requests_mock):
    requests_mock.get(
        f"{API_BASE}/buildInfo",
        headers={"Content-Type": "application/json"},
        json={
            "payload": {
                "specVersion": "7.7.0",
                "buildNumber": "branch: main f2731e315ee137cf94c48e5f2fa431777fe49cef",
                "platformVersion": "8.23.0",
            },
            "errorMessages": [],
        },
    )

    requests_mock.get(
        f"{API_EXPERIMENTAL}/textanalysis/containers/container",
        headers={"Content-Type": "application/json"},
        json={
            "payload": {
                "containerName": "container",
                "scope": "GLOBAL",
                "resources": [
                    {"relativePath": "text3.txt"},
                    {"relativePath": "text2.txt"},
                    {"relativePath": "text1.txt"},
                    {"relativePath": "sub/text4.txt"},
                ],
            },
            "errorMessages": [],
        },
    )

    resource_container = ResourceContainer(
        client, "container", "GLOBAL", "experimental/textanalysis/containers"
    )
    actual_resources = resource_container.list_resources()
    assert len(actual_resources) == 4
    assert "text3.txt" in actual_resources
    assert "text2.txt" in actual_resources
    assert "text1.txt" in actual_resources
    assert "sub/text4.txt" in actual_resources


def test_export_resources(tmp_path, client, requests_mock):
    requests_mock.get(
        f"{API_BASE}/buildInfo",
        headers={"Content-Type": "application/json"},
        json={
            "payload": {
                "specVersion": "7.7.0",
                "buildNumber": "branch: main f2731e315ee137cf94c48e5f2fa431777fe49cef",
                "platformVersion": "8.23.0",
            },
            "errorMessages": [],
        },
    )

    example_text = "some text"
    requests_mock.get(
        f"{API_EXPERIMENTAL}/textanalysis/containers/container",
        headers={"Content-Type": "application/zip"},
        text=example_text,
    )

    target_zip_file = tmp_path / "target_zip.zip"
    resource_container = ResourceContainer(
        client, "container", "GLOBAL", "experimental/textanalysis/containers"
    )
    resource_container.export_resources(target_zip_file)

    assert target_zip_file.exists()
    assert example_text == target_zip_file.read_text()


def test_export_resource(tmp_path, client, requests_mock):
    requests_mock.get(
        f"{API_BASE}/buildInfo",
        headers={"Content-Type": "application/json"},
        json={
            "payload": {
                "specVersion": "7.7.0",
                "buildNumber": "branch: main f2731e315ee137cf94c48e5f2fa431777fe49cef",
                "platformVersion": "8.23.0",
            },
            "errorMessages": [],
        },
    )

    example_text = "some text"
    requests_mock.get(
        f"{API_EXPERIMENTAL}/textanalysis/containers/container/resources",
        text=example_text,
    )

    target_file = tmp_path / "target.txt"
    resource_container = ResourceContainer(
        client, "container", "GLOBAL", "experimental/textanalysis/containers"
    )
    resource_container.export_resource(target_file, "test/target.txt")

    assert target_file.exists()
    assert example_text == target_file.read_text()


def test_upsert_resource(client, requests_mock):
    requests_mock.get(
        f"{API_BASE}/buildInfo",
        headers={"Content-Type": "application/json"},
        json={
            "payload": {
                "specVersion": "7.7.0",
                "buildNumber": "branch: main f2731e315ee137cf94c48e5f2fa431777fe49cef",
                "platformVersion": "8.23.0",
            },
            "errorMessages": [],
        },
    )

    requests_mock.post(
        f"{API_EXPERIMENTAL}/textanalysis/containers/container/resources",
        headers={"Content-Type": "application/json"},
        json={
            "payload": {},
            "errorMessages": [],
        },
    )

    resource_file = Path(TEST_DIRECTORY) / "resources" / "texts" / "text1.txt"
    resource_container = ResourceContainer(
        client, "container", "GLOBAL", "experimental/textanalysis/containers"
    )
    resource_container.upsert_resource(resource_file, "test/text1.txt")


def test_delete_resource(client, requests_mock):
    requests_mock.get(
        f"{API_BASE}/buildInfo",
        headers={"Content-Type": "application/json"},
        json={
            "payload": {
                "specVersion": "7.7.0",
                "buildNumber": "branch: main f2731e315ee137cf94c48e5f2fa431777fe49cef",
                "platformVersion": "8.23.0",
            },
            "errorMessages": [],
        },
    )

    requests_mock.delete(
        f"{API_EXPERIMENTAL}/textanalysis/containers/container/resources",
        headers={"Content-Type": "application/json"},
        json={
            "payload": {},
            "errorMessages": [],
        },
    )

    resource_container = ResourceContainer(
        client, "container", "GLOBAL", "experimental/textanalysis/containers"
    )
    resource_container.delete_resource("test/text1.txt")


def test_delete_resource_container(client, requests_mock):
    requests_mock.get(
        f"{API_BASE}/buildInfo",
        headers={"Content-Type": "application/json"},
        json={
            "payload": {
                "specVersion": "7.7.0",
                "buildNumber": "branch: main f2731e315ee137cf94c48e5f2fa431777fe49cef",
                "platformVersion": "8.23.0",
            },
            "errorMessages": [],
        },
    )

    requests_mock.delete(
        f"{API_EXPERIMENTAL}/textanalysis/containers/container",
        headers={"Content-Type": "application/json"},
        json={
            "payload": {},
            "errorMessages": [],
        },
    )

    resource_container = ResourceContainer(
        client, "container", "GLOBAL", "experimental/textanalysis/containers"
    )
    resource_container.delete()
