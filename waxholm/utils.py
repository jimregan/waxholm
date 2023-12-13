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


def clean_silences_mfa(pron, non_phones=False):
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
    NON_PHONES = ["v", "kl", "SIL", "pa", "sm"]
    if non_phones:
        split = [x for x in split if x not in NON_PHONES]
    return " ".join(split[start:end+1])


def clean_pronunciation(text, non_phones=False):
    text = fix_duration_markers(text)
    text = strip_accents(text)
    text = replace_glottal_closures(text)
    text = clean_silences_mfa(text, non_phones)
    return text


def clean_pron_set(prons, non_phones=False):
    output = set()
    for pron in prons:
        output.add(clean_pronunciation(pron, non_phones))
    return output


def is_x_word(text):
    return len(text) >= 2 and text[0] == "X" and text[-1] == "X"


def cond_lc(text):
    if is_x_word(text):
        return text
    else:
        return text.lower()


IPA_MAPPING = {
    "2D": "ɖ",
    "2L": "ɭ",
    "2N": "ɳ",
    "2S": "ʂ",
    "2T": "ʈ",
    "A": "a",
    "A:": "ɑː",
    "B": "b",
    "D": "d",
    "E": "e",
    "E0": "ə",
    "E:": "eː",
    "F": "f",
    "G": "ɡ",
    "H": "h",
    "I": "ɪ",
    "I:": "iː",
    "J": "j",
    "K": "k",
    "L": "l",
    "M": "m",
    "N": "n",
    "NG": "ŋ",
    "O": "ʊ",
    "O:": "uː",
    "P": "p",
    "R": "r",
    "S": "s",
    "SJ": "ɧ",
    "T": "t",
    "TJ": "ɕ",
    "U": "ɵ",
    "U:": "ʉː",
    "V": "v",
    "Y": "ʏ",
    "Y:": "yː",
    "Ä": "ɛ",
    "Ä3": "æː",
    "Ä4": "æ",
    "Ä:": "ɛː",
    "Ö": "œ",
    "Ö3": "œ̞ː",
    "Ö4": "œ̞",
    "Ö:": "øː",
    "Å": "ɔ",
    "Å:": "oː"
}


def map_to_ipa(phone_list, non_speech=False):
    output = []
    for phone in phone_list:
        if phone in IPA_MAPPING:
            output.append(IPA_MAPPING[phone])
        elif non_speech:
            output.append(f"<{phone}>")
    return output
