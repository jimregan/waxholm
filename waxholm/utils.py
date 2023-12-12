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
    LOCAL_SILS = {f" {x} {SILS[x]} ": f" {x} " for x in SILS}
    for retro in ["D", "T"]:
        LOCAL_SILS[f" 2{retro} {retro.lower()} "] = f" 2{retro} "
        LOCAL_SILS[f" {retro} 2{retro.lower()} "] = f" 2{retro} "
    for sil in LOCAL_SILS:
        if sil in input:
            input = input.replace(sil, LOCAL_SILS[sil])
            input = f" {input.strip()} "
    return input.strip()


def strip_accents(text):
    for accent in "ˈ`ˌ":
        text = text.replace(accent, "")
    return text


def clean_silences_mfa(pron, vowellike=False):
    if pron == "p:":
        return "SIL"
    split = pron.split(" ")
    start = 0
    end = len(split) - 1
    if split[start] == "p:":
        start += 1
    if split[end] == "p:":
        end -= 1
    split = ["SIL" if x == "p:" else x for x in split]
    if vowellike:
        split = [x for x in split if x != "v"]
    return " ".join(split[start:end+1])


def clean_pronunciation(text, vowellike=False):
    text = fix_duration_markers(text)
    text = strip_accents(text)
    text = replace_glottal_closures(text)
    text = clean_silences_mfa(text, vowellike)
    return text


def clean_pron_set(prons, vowellike=False):
    output = set()
    for pron in prons:
        output.add(clean_pronunciation(pron, vowellike))
    return output


def cond_lc(text):
    if len(text) >= 2 and text[0] == "X" and text[-1] == "X":
        return text
    else:
        return text.lower()
