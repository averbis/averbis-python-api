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
from typing import Iterable, Dict

import sys

COLOR_LIST = {
    "Color_off": "\033[0m",  # Restores previous black color
    "Black": "\033[0;30m",  # Black
    "Red": "\033[0;31m",  # Red
    "Green": "\033[0;32m",  # Green
    "Yellow": "\033[0;33m",  # Yellow
    "Blue": "\033[0;34m",  # Blue
    "Purple": "\033[0;35m",  # Purple
    "Cyan": "\033[0;36m",  # Cyan
    "White": "\033[0;37m",  # White
    # Bold
    "BBlack": "\033[1;30m",  # Black
    "BRed": "\033[1;31m",  # Red
    "BGreen": "\033[1;32m",  # Green
    "BYellow": "\033[1;33m",  # Yellow
    "BBlue": "\033[1;34m",  # Blue
    "BPurple": "\033[1;35m",  # Purple
    "BCyan": "\033[1;36m",  # Cyan
    "BWhite": "\033[1;37m",  # White
    # Underline
    "UBlack": "\033[4;30m",  # Black
    "URed": "\033[4;31m",  # Red
    "UGreen": "\033[4;32m",  # Green
    "UYellow": "\033[4;33m",  # Yellow
    "UBlue": "\033[4;34m",  # Blue
    "UPurple": "\033[4;35m",  # Purple
    "UCyan": "\033[4;36m",  # Cyan
    "UWhite": "\033[4;37m",  # White
    # Background
    "On_Black": "\033[40m",  # Black
    "On_Red": "\033[41m",  # Red
    "On_Green": "\033[42m",  # Green
    "On_Yellow": "\033[43m",  # Yellow
    "On_Blue": "\033[44m",  # Blue
    "On_Purple": "\033[45m",  # Purple
    "On_Cyan": "\033[46m",  # Cyan
    "On_White": "\033[47m",  # White
    # High Intensity
    "IBlack": "\033[0;90m",  # Black
    "IRed": "\033[0;91m",  # Red
    "IGreen": "\033[0;92m",  # Green
    "IYellow": "\033[0;93m",  # Yellow
    "IBlue": "\033[0;94m",  # Blue
    "IPurple": "\033[0;95m",  # Purple
    "ICyan": "\033[0;96m",  # Cyan
    "IWhite": "\033[0;97m",  # White
    # Bold High Intensity
    "BIBlack": "\033[1;90m",  # Black
    "BIRed": "\033[1;91m",  # Red
    "BIGreen": "\033[1;92m",  # Green
    "BIYellow": "\033[1;93m",  # Yellow
    "BIBlue": "\033[1;94m",  # Blue
    "BIPurple": "\033[1;95m",  # Purple
    "BICyan": "\033[1;96m",  # Cyan
    "BIWhite": "\033[1;97m",  # White
    # High Intensty backgrounds
    "On_IBlack": "\033[0;100m",  # Black
    "On_IRed": "\033[0;101m",  # Red
    "On_IGreen": "\033[0;102m",  # Green
    "On_IYellow": "\033[0;103m",  # Yellow
    "On_IBlue": "\033[0;104m",  # Blue
    "On_IPurple": "\033[10;95m",  # Purple
    "On_ICyan": "\033[0;106m",  # Cyan
    "On_IWhite": "\033[0;107m",  # White
}


def highlight_matches(
    document_text: str, matches: Iterable, highlight_color: str = "On_Green"
) -> None:
    pass
    """
    Highlights a list of annotations in a given document. Annotations must not overlap.

    :document_text: Document text that contains annotation
    :annotation: Annotation that should be highlighted. Needs begin/end/coveredText.
    """
    last_position = 0
    for match in sorted(matches, key=lambda match: match.start()):
        sys.stdout.write(document_text[last_position : match.start()])
        sys.stdout.write(
            _render_highlighted(
                document_text,
                max(last_position, match.start()),
                match.end(),
                highlight_color=highlight_color,
            )
        )

        last_position = max(match.end(), last_position)

    sys.stdout.write(document_text[last_position:])


def highlight_match(
    document_text: str,
    regexp_match,
    context_size: int = 300,
    highlight_color: str = "On_Green",
) -> None:
    """
    Highlighting a regular expression match (from python library re) in given document.

    :document_text: Document text that contains annotation
    :annotation: Annotation that should be highlighted. Needs begin/end.
    :window_size: Number of chars before and after the annotation to be displayed. Set window_size to float("inf") for complete text.
    :highlighting_color: Highlighting color (default is green) which is taken from get_text_color_from_list.
    """

    sys.stdout.write(
        _render_highlighted(
            document_text,
            regexp_match.start(),
            regexp_match.end(),
            context_size,
            highlight_color,
        )
    )


def highlight_annotations(
    document_text: str, annotations: Iterable[Dict], highlight_color: str = "On_Green"
) -> None:
    """
    Highlights a list of annotations in a given document. Annotations must not overlap.

    :document_text: Document text that contains annotation
    :annotation: Annotation that should be highlighted. Needs begin/end/coveredText.
    """
    last_position = 0
    for annotation in sorted(annotations, key=lambda ann: ann["begin"]):
        sys.stdout.write(document_text[last_position : annotation["begin"]])
        sys.stdout.write(
            _render_highlighted(
                document_text,
                max(last_position, annotation["begin"]),
                annotation["end"],
                highlight_color=highlight_color,
            )
        )

        last_position = max(last_position, annotation["end"])

    sys.stdout.write(document_text[last_position:])


def highlight_annotation(
    document_text: str,
    annotation: Dict,
    context_size: int = 300,
    highlight_color: str = "On_Green",
) -> None:
    """
    Highlights annotation in given document.

    :document_text: Document text that contains annotation
    :annotation: Annotation that should be highlighted. Needs begin/end.
    :window_size: Number of chars before and after the annotation to be displayed. Set window_size to float("inf") for complete text.
    :highlighting_color: Highlighting color (default is green) which is taken from get_text_color_from_list.
    """

    sys.stdout.write(
        _render_highlighted(
            document_text, annotation["begin"], annotation["end"], context_size, highlight_color
        )
    )


def _render_highlighted(
    document_text: str,
    begin: int,
    end: int,
    context_size: int = 0,
    highlight_color: str = "On_Green",
) -> str:
    """Actual internal print method that assembles the output string."""
    black_color = _get_text_color_from_list("Color_off")
    return (
        document_text[begin - context_size : begin]
        + _get_text_color_from_list(highlight_color)
        + document_text[begin:end]
        + black_color
        + document_text[end : end + context_size]
    )


def _get_text_color_from_list(color_name):
    if color_name in COLOR_LIST:
        return COLOR_LIST[color_name]
    else:
        print(f"Color {color_name} not found. Returning black as color.")
        return COLOR_LIST["Black"]
