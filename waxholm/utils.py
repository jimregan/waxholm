# Copyright (c) 2023, Jim O'Regan for Språkbanken Tal
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


X_TAGS = {
    "XtvekX": "öh",
    "XinandX": "pa",
    "XsmackX": "sm",
    "XutandX": "pa",
    "XharklingX": "ha",
    "XklickX": "kl",
    "XavbrordX": "",
    "XskrattX": "ha",
    "XsuckX": "pa"
}


def check_x_tag(word, phoneme):
    if word == "XavbrordX":
        return True
    if word in X_TAGS:
        return phoneme == X_TAGS[word]


def clean_x_words(words):
    """Removes 'X' words (non-spoken noise markers) from the text

    Args:
        words (List[str]): list of words to clean
    """
    def clean_x_word(word):
        if "XX" in word:
            return ""
        elif word.startswith("X") and word.endswith("X"):
            return ""
        else:
            return word
    return [x for x in words if clean_x_word(x) != ""]


def fix_duration_markers(input):
    input += ' '
    input = input.replace(":+ ", ": ")
    input = input.replace("+ ", " ")
    return input.strip()


SILS = {
    "K": "k",
    "G": "g",
    "T": "t",
    "D": "d",
    "2T": "2t",
    "2D": "2d",
    "P": "p",
    "B": "b"
}


def is_glottal_closure(cur, next):
    return cur in SILS and next == SILS[cur]


def replace_glottal_closures(input):
    input = f" {input} "
    for sil in SILS:
        input = input.replace(f" {sil} {SILS[sil]} ", f" {sil} ")
        if "2" in sil:
            sil_no_two = sil.replace("2", "")
            input = input.replace(f" {sil_no_two} {SILS[sil]} ", f" {sil} ")
    return input.strip()
