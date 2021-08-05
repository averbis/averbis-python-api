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


def assert_process_equal(expected_process: "Process", actual_process: "Process"):
    assert expected_process.name == actual_process.name
    assert expected_process.project.name == actual_process.project.name
    assert expected_process.pipeline_name == actual_process.pipeline_name
    assert expected_process.document_source_name == actual_process.document_source_name
    assert expected_process.preceding_process_name == actual_process.preceding_process_name
