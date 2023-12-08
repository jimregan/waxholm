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
from collections import namedtuple
from copy import deepcopy
from .exceptions import FRExpected
from difflib import SequenceMatcher
import re


def fix_text(text: str, extended: bool = False) -> str:
    replacements = text.maketrans("{}|\\[]", "äåöÖÄÅ")
    if not extended:
        return text.translate(replacements)
    else:
        tr = text.translate(replacements)
        spaced = re.sub("\s+", " ", tr)
        if spaced[-1] == ".":
            spaced = spaced[:-1]
        return spaced.strip()


Label = namedtuple('Label', ['start', 'end', 'label'])


class FR:
    def __init__(self, text="", **kwargs):  # C901
        if text and text != "":
            self.from_text(text)
        else:
            for arg in kwargs:
                prms = ["pm", "pm_type", "type", "frame",
                        "seconds", "phone", "phone_type",
                        "word", "pseudoword"]
                if arg in prms:
                    self.__dict__[arg] = kwargs[arg]
                else:
                    print(f"Unrecognised argument: {arg}")

    def from_text(self, text: str):
        if not text.startswith("FR"):
            raise FRExpected(text)
        parts = [a.strip() for a in text.split("\t")]
        if not parts[0].startswith("FR"):
            print("Error with FR", text)
        self.frame = parts[0][2:].strip()
        if parts[-1].strip().endswith(" sec"):
            self.seconds = parts[-1].strip()[0:-4]
        def split_phone(phone):
            if phone.startswith("$#"):
                phtype = 'I'
                phone_type = fix_text(phone[0:2])
                phone_out = fix_text(phone[2:])
            elif phone.startswith("$") or phone.startswith("#"):
                phtype = 'I'
                phone_type = fix_text(phone[0:1])
                phone_out = fix_text(phone[1:])
            else:
                return None
            return {
                "type": phtype,
                "phone_type": phone_type,
                "phone": phone_out
            }
        for subpart in parts[1:-1]:
            subpart = subpart.strip()
            if subpart.startswith("$#") or subpart.startswith("$") or subpart.startswith("#"):
                phparts = split_phone(subpart)
                if phparts is not None:
                    self.type = phparts['type']
                    self.phone_type = phparts['phone_type']
                    self.phone = phparts['phone']
            elif subpart.startswith(">pm "):
                phparts = split_phone(subpart[4:])
                if phparts is not None:
                    self.pm_type = phparts['phone_type']
                    self.pm = phparts['phone']
            elif subpart.startswith(">pm. "):
                phparts = split_phone(subpart[5:])
                if phparts is not None:
                    self.pm_type = phparts['phone_type']
                    self.pm = phparts['phone']
            elif subpart.startswith(">w "):
                self.type = 'B'
                self.word = fix_text(subpart[3:])
                self.pseudoword = False
            elif subpart.startswith(">w. 1.038"):
                self.type = 'B'
                self.word = fix_text(".")
                self.pseudoword = False
            elif subpart.startswith(">w. "):
                self.type = 'B'
                self.word = fix_text(subpart[4:])
                self.pseudoword = False
            elif subpart == "> XklickX" or subpart == "> XutandX":
                self.type = 'B'
                self.word = subpart[2:]
                self.pseudoword = True
            elif subpart.startswith("X"):
                if hasattr(self, 'type'):
                    print(self.type, self.type == 'B')
                self.type = getattr(self, 'type', 'B')
                self.word = fix_text(subpart)
                self.pseudoword = True
            elif subpart == "OK":
                self.type = 'E'
            elif subpart == "PROBLEMS":
                self.type = 'E'

    def get_type(self):
        if "type" in self.__dict__:
            return self.type
        else:
            return ""

    def __repr__(self):
        parts = []
        parts.append(f"type: {self.get_type()}")
        parts.append(f"frame: {self.frame}")
        if self.get_type() != 'E':
            parts.append(f"phone: {self.get_phone()}")
        if 'word' in self.__dict__:
            parts.append(f"word: {self.word}")
        if 'pm_type' in self.__dict__:
            parts.append(f"pm_type: {self.pm_type}")
        if 'pm' in self.__dict__:
            parts.append(f"pm: {self.pm}")
        if 'seconds' in self.__dict__:
            parts.append(f"sec: {self.seconds}")
        return "FR(" + ", ".join(parts) + ")"

    def fix_type(self):
        if not "type" in self.__dict__:
            if "pm_type" in self.__dict__ and self.pm_type == "$":
                self.type = "B"
        if self.is_type("B") and self.get_word() == "":
            self.pm_type = "$"
            self.phone_type = "$"
            self.type = "I"

    def get_phone(self, fix_accents=True):
        def fix_accents(phone, fix_accents=True):
            if not fix_accents:
                return phone
            return phone.replace("'", "ˈ").replace('"', "ˌ")
        if 'pm' in self.__dict__:
            return fix_accents(self.pm, fix_accents)
        elif 'phone' in self.__dict__:
            return fix_accents(self.phone, fix_accents)
        else:
            return None

    def is_silence_word(self, noise=False):
        if 'word' in self.__dict__:
            if not noise:
                return self.word == "XX"
            else:
                return self.word.startswith("X") and self.word.endswith("X")
        else:
            return False
    
    def is_type(self, type):
        if "type" in self.__dict__:
            return type == self.type
        else:
            return False

    def has_seconds(self):
        return "seconds" in self.__dict__

    def get_seconds(self):
        if not self.has_seconds() and "frame" in self.__dict__:
            return int(self.frame) / 16000.0
        else:
            return self.seconds

    def get_word(self):
        if self.has_word():
            return self.word
        else:
            return ""

    def has_word(self):
        return "word" in self.__dict__

    def has_pseudoword(self):
        return "pseudoword" in self.__dict__


def merge_frs(fr1, fr2, check_time=False):
    """
    Merge FRS entries for plosives: by default, the
    period of glottal closure and the burst are separately
    annotated.
    """
    if fr2.has_word():
        return None
    if check_time:
        if fr1.get_seconds() != fr2.get_seconds():
            return None
    if _is_glottal_closure(fr1.get_phone(), fr2.get_phone()):
        if not fr1.has_word():
            return fr2
        else:
            word = None
            if fr1.has_word():
                word = fr1.word
            pword = None
            if fr1.has_pseudoword():
                pword = fr1.pseudoword
            return FR(pm=fr2.pm, pm_type=fr2.pm_type, type=fr2.type,
                      frame=fr2.frame, seconds=fr2.seconds, phone=fr2.phone,
                      phone_type=fr2.phone_type, word=word, pseudoword=pword)


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
def _is_glottal_closure(cur, next):
    return cur in SILS and next == SILS[cur]


def _replace_glottal_closures(input):
    input = f" {input} "
    for sil in SILS:
        input = input.replace(f" {sil} {SILS[sil]} ", f" {sil} ")
        if "2" in sil:
            sil_no_two = sil.replace("2", "")
            input = input.replace(f" {sil_no_two} {SILS[sil]} ", f" {sil} ")            
    return input.strip()


def _fix_duration_markers(input):
    input += ' '
    input = input.replace(":+ ", ": ")
    return input[:-1]


class Mix():
    def __init__(self, filepath: str, stringfile=None, fix_type=True):
        self.fr = []
        self.path = filepath
        if stringfile is None:
            with open(filepath) as inpf:
                self.read_data(inpf.readlines())
        else:
            self.read_data(stringfile.split("\n"))
        if fix_type:
            for fr in self.fr:
                fr.fix_type()

    def read_data(self, inpf):  # C901
        """read data from text of a .mix file"""
        saw_text = False
        saw_phoneme = False
        saw_labels = False
        for line in inpf:
            if line.startswith("Waxholm dialog."):
                self.filepath = line[15:].strip()
            if line.startswith("TEXT:"):
                saw_text = True
                continue
            if saw_text:
                self.text = fix_text(line.strip())
                saw_text = False
            if line.startswith("PHONEME:"):
                saw_phoneme = True
                self.phoneme = fix_text(line[8:].strip())
                if line[8:].strip().endswith("."):
                    saw_phoneme = False
                continue
            if saw_phoneme:
                self.phoneme = fix_text(line.strip())
                if line[8:].strip().endswith("."):
                    saw_phoneme = False
            if line.startswith("FR "):
                if saw_labels:
                    saw_labels = False
                self.fr.append(FR(text=line))
            if line.startswith("Labels: "):
                self.labels = line[8:].strip()
                saw_labels = True
            if saw_labels and line.startswith(" "):
                self.labels += line.strip()

    def check_fr(self, verbose=False) -> bool:
        """
        Simple sanity check: that there were FR lines,
        and that the first was a start type, and
        last was an end type.
        """
        if 'fr' not in self.__dict__:
            return False
        if len(self.fr) == 0:
            return False
        start_end = self.fr[0].is_type("B") and self.fr[-1].is_type("E")
        if verbose and not start_end:
            if not self.fr[0].is_type("B"):
                print(f"{self.path}: missing start type")
            if not self.fr[-1].is_type("E"):
                print(f"{self.path}: missing end type")
        return start_end

    def get_times(self, as_frames=False):
        """
        get the times of each phoneme
        """
        if not self.check_fr(verbose=True):
            return []
        if as_frames:
            times = [int(x.frame) for x in self.fr]
        else:
            times = [float(x.seconds) for x in self.fr]
        return times

    def get_time_pairs(self, as_frames=False):
        """
        get a list of tuples containing start and end times
        By default, the times are in seconds; if `as_frames`
        is set, the number of frames are returned instead.
        """
        times = self.get_times(as_frames=as_frames)
        starts = times[0:-1]
        ends = times[1:]
        return [x for x in zip(starts, ends)]

    def prune_empty_presilences(self, verbose=False, include_noises=False):
        """
        Remove empty silence markers (i.e., those with no distinct duration)
        """
        self.orig_fr = deepcopy(self.fr)
        i = 0
        warned = False
        def check_cur(cur, next):
            if verbose and not cur.has_seconds():
                print(f"Missing seconds: {self.path}\nLine: {cur}")
            if verbose and not next.has_seconds():
                print(f"Missing seconds: {self.path}\nLine: {next}")
            return cur.get_seconds() == next.get_seconds() and cur.is_silence_word()
        todel = []
        while i < len(self.fr) - 1:
            if check_cur(self.fr[i], self.fr[i + 1]):
                if verbose:
                    if not warned:
                        warned = True
                        print(f"Empty silence in {self.path}:")
                    print(self.fr[i])
                todel.append(i)
            i += 1
        if todel is not None and todel != []:
            for chaff in todel.reverse():
                del(self.fr[chaff])

    def prune_empty_postsilences(self, verbose=False, include_noises=False):
        """
        Remove empty silence markers (i.e., those with no distinct duration)
        """
        if not "orig_fr" in self.__dict__:
            self.orig_fr = deepcopy(self.fr)
        i = 1
        warned = False
        def check_cur(cur, prev):
            if verbose and not cur.has_seconds():
                print(f"Missing seconds: {self.path}\nLine: {cur}")
            if verbose and not prev.has_seconds():
                print(f"Missing seconds: {self.path}\nLine: {prev}")
            return cur.get_seconds() == prev.get_seconds() and cur.is_silence_word()
        todel = []
        while i < len(self.fr):
            if check_cur(self.fr[i], self.fr[i - 1]):
                if verbose:
                    if not warned:
                        warned = True
                        print(f"Empty silence in {self.path}:")
                    print(self.fr[i])
                todel.append(i)
            i += 1
        if todel is not None and todel != []:
            for chaff in todel.reverse():
                del(self.fr[chaff])

    def prune_empty_segments(self, verbose=False):
        """
        Remove empty segments (i.e., those with no distinct duration)
        """
        if not "orig_fr" in self.__dict__:
            self.orig_fr = deepcopy(self.fr)
        times = self.get_time_pairs(as_frames=True)
        if len(times) != (len(self.fr) - 1):
            print("Uh oh: time pairs and items don't match")
        else:
            keep = []
            for fr in zip(self.fr[:-1], times):
                cur_time = fr[1]
                if cur_time[0] == cur_time[1]:
                    if verbose:
                        print(f"Empty segment {fr[0].get_phone()} ({cur_time[0]} --> {cur_time[1]})")
                else:
                    keep.append(fr[0])
            keep.append(self.fr[-1])
            self.fr = keep

    def prune_empty_silences(self, verbose = False):
        self.prune_empty_presilences(verbose)
        self.prune_empty_postsilences(verbose)

    def merge_plosives(self, verbose=False):
        """
        Merge plosives in FRs
        (in Waxholm, as in TIMIT, the silence before the burst and the burst
        are annotated separately).
        """
        if not "orig_fr" in self.__dict__:
            self.orig_fr = deepcopy(self.fr)
        tmp = []
        i = 0
        while i < len(self.fr)-1:
            merged = merge_frs(self.fr[i], self.fr[i+1])
            if merged is not None:
                if verbose:
                    print(f"Merging {self.fr[i]} and {self.fr[i+1]}")
                i += 1
                tmp.append(merged)
            else:
                tmp.append(self.fr[i])
            i += 1
        tmp.append(self.fr[-1])
        self.fr = tmp

    def get_phone_label_tuples(self, as_frames=False, fix_accents=True):
        times = self.get_time_pairs(as_frames=as_frames)
        if self.check_fr():
            labels = [fr.get_phone(fix_accents) for fr in self.fr[0:-1]]
        else:
            labels = []
        if len(times) == len(labels):
            out = []
            for z in zip(times, labels):
                out.append((z[0][0], z[0][1], z[1]))
            return out
        else:
            return []

    def get_merged_plosives(self, noop=False, prune_empty=True):
        """
        Returns a list of phones with plosives merged
        (in Waxholm, as in TIMIT, the silence before the burst and the burst
        are annotated separately).
        If `noop` is True, it simply returns the output of `prune_empty_labels()`
        """
        if noop:
            if not prune_empty:
                print("Warning: not valid to set noop to True and prune_empty to false")
                print("Ignoring prune_empty")
            return self.prune_empty_labels()
        i = 0
        out = []
        if prune_empty:
            labels = self.prune_empty_labels()
        else:
            labels = self.get_phone_label_tuples()
        while i < len(labels)-1:
            cur = labels[i]
            next = labels[i+1]
            if _is_glottal_closure(cur[2], next[2]):
                tmp = Label(start = cur[0], end = next[1], label = next[2])
                out.append(tmp)
                i += 2
            else:
                tmp = Label(start = cur[0], end = cur[1], label = cur[2])
                out.append(tmp)
                i += 1
        return out

    def get_word_label_tuples(self, verbose=True):
        times = self.get_time_pairs()
        if len(times) == len(self.fr[0:-1]):
            out = []
            labels_raw = [x for x in zip(times, self.fr[0:-1])]
            i = 0
            cur = None
            while i < len(labels_raw) - 1:
                if labels_raw[i][1].is_type("B"):
                    if cur is not None:
                        out.append(cur)
                    if labels_raw[i+1][1].is_type("B"):
                        if verbose and labels_raw[i][1].get_word() == "":
                            print("Expected word", labels_raw[i][1])
                        out.append((labels_raw[i][0][0], labels_raw[i][0][1], labels_raw[i][1].get_word()))
                        cur = None
                        i += 1
                        continue
                    else:
                        if verbose and labels_raw[i][1].get_word() == "":
                            print("Expected word", labels_raw[i][1])
                        cur = (labels_raw[i][0][0], labels_raw[i][0][1], labels_raw[i][1].get_word())
                if labels_raw[i+1][1].is_type("B"):
                    if cur is not None:
                        cur = (cur[0], labels_raw[i][0][1], cur[2])
                i += 1
            out.append(cur)
            return out
        else:
            return []

    def get_dictionary(self, fix_accents=True):
        """
        Get pronunciation dictionary entries from the .mix file.
        These entries are based on the corrected pronunciations; for
        the lexical pronunciations, use the `phoneme` property.
        """
        output = {}
        current_phones = []
        prev_word = ''

        for fr in self.fr:
            if 'word' in fr.__dict__:
                phone = fr.get_phone(fix_accents)
                if prev_word != "":
                    if prev_word not in output:
                        output[prev_word] = []
                    output[prev_word].append(current_phones.copy())
                    current_phones.clear()
                prev_word = fr.word
                current_phones.append(phone)
            elif fr.is_type("I"):
                phone = fr.get_phone(fix_accents)
                current_phones.append(phone)
            else:
                if prev_word not in output:
                    output[prev_word] = []
                output[prev_word].append(current_phones.copy())
                return output

    def get_dictionary_list(self, fix_accents=True):
        """
        Get pronunciation dictionary entries from the .mix file.
        These entries are based on the corrected pronunciations; for
        the lexical pronunciations, use the `phoneme` property.
        This version creates a list of tuples (word, phones) that
        preserves the order of the entries.
        """
        output = []
        current_phones = []
        prev_word = ''

        for fr in self.fr:
            if 'word' in fr.__dict__:
                phone = fr.get_phone(fix_accents)
                if prev_word != "":
                    output.append((prev_word, " ".join(current_phones)))
                    current_phones.clear()
                prev_word = fr.word
                current_phones.append(phone)
            elif fr.is_type("I"):
                phone = fr.get_phone(fix_accents)
                current_phones.append(phone)
            else:
                output.append((prev_word, " ".join(current_phones)))
                return output

    def get_phoneme_string(self, insert_pauses=True, fix_accents=True):
        """
        Get an opinionated phoneme string

        Args:
            insert_pauses (bool, optional): Insert pauses between words. Defaults to True.
            fix_accents (bool, optional): IPA-ify accents. Defaults to True.
        """
        dict_list = self.get_dictionary_list(fix_accents)
        skip = ['p:', '.']
        if insert_pauses:
            phone_strings = [x[1] for x in dict_list if x[1] not in skip]
            joined = ' p: '.join(phone_strings)
        else:
            phone_strings = [x[1] for x in dict_list if x[1] != "."]
            joined = ' '.join(phone_strings)
        joined = _replace_glottal_closures(joined)
        joined = _fix_duration_markers(joined)
        return joined

    def get_phoneme_list(self, insert_pauses=True, fix_accents=True):
        return self.get_phoneme_string(insert_pauses, fix_accents).split(' ')

    def get_compare_dictionary(self, fix_accents=True, merge_plosives=True, only_changed=True):
        """
        Get pronunciation dictionary for comparision: i.e., where there is a difference
        between the canonical pronunciation and what was spoken
        """
        if merge_plosives:
            self.merge_plosives()
        orig = self.get_dictionary_list(fix_accents)
        self.prune_empty_segments()
        new = self.get_dictionary_list(fix_accents)
        if len(orig) != len(new):
            words_orig = [w[0] for w in orig]
            words_new = [w[0] for w in new]
            skippables = []
            for tag, i, j, _, _ in SequenceMatcher(None, words_orig, words_new).get_opcodes():
                if tag in ('delete', 'replace'):
                    skippables += [a for a in range(i, j)]
            for c in skippables.reverse():
                del(orig[c])
        out = []
        i = 0
        while i < len(orig):
            if orig[i][0] == new[i][0]:
                if orig[i][1] == new[i][1]:
                    if not only_changed:
                        out.append(orig)
                else:
                    out.append((orig[i][0], orig[i][1], new[i][1]))
            i += 1
        return out
