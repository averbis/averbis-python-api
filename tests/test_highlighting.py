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
import re

from averbis.highlighting import (
    highlight_match,
    highlight_matches,
    highlight_annotation,
    highlight_annotations,
)


def test_highlight_match(capfd):
    document_text = "This is a test."
    m = re.search("\\bis\\b", document_text)
    highlight_match(document_text, m, 4)

    out, err = capfd.readouterr()
    assert out == "his \x1b[42mis\x1b[0m a t"


def test_highlight_matches(capfd):
    document_text = "This is a test with two is "
    m = re.finditer("\\bis\\b", document_text)
    highlight_matches(document_text, m)

    out, err = capfd.readouterr()
    assert out == "This \x1b[42mis\x1b[0m a test with two \x1b[42mis\x1b[0m "


def test_overlapping_matches(capfd):
    document_text = "long number 2030."
    m = re.finditer(r"\d{2}", document_text)
    highlight_matches(document_text, m)

    out, err = capfd.readouterr()
    assert out == "long number \x1b[42m20\x1b[0m\x1b[42m30\x1b[0m."
    print(out)


def test_highlight_annotation(capfd):
    document_text = "This is a test."
    annotation = {"begin": 5, "end": 7}
    highlight_annotation(document_text, annotation, 4)

    out, err = capfd.readouterr()
    assert out == "his \x1b[42mis\x1b[0m a t"


def test_highlight_annotations(capfd):
    document_text = "This is a test."
    annotations = [{"begin": 5, "end": 7}, {"begin": 10, "end": 14}]
    highlight_annotations(document_text, annotations)

    out, err = capfd.readouterr()
    assert out == "This \x1b[42mis\x1b[0m a \x1b[42mtest\x1b[0m."
