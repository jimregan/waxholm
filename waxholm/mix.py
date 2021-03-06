from .exceptions import FRExpected


def fix_text(text: str) -> str:
    replacements = text.maketrans("{}|\\[]", "äåöÖÄÅ")
    return text.translate(replacements)


class FR:
    def __init__(self, text: str):  # C901
        if not text.startswith("FR"):
            raise FRExpected(text)
        parts = [a.strip() for a in text.split("\t")]
        self.frame = parts[0][2:].strip()
        if parts[-1].strip().endswith(" sec"):
            self.seconds = parts[-1].strip()[0:-4]
        for subpart in parts[1:-1]:
            if subpart.startswith("$#"):
                self.type = 'I'
                self.phone_type = fix_text(subpart[0:2])
                self.phone = fix_text(subpart[2:])
            elif subpart.startswith("$"):
                self.type = 'I'
                self.phone_type = fix_text(subpart[0:1])
                self.phone = fix_text(subpart[1:])
            elif subpart.startswith("#"):
                self.type = 'B'
                self.phone_type = fix_text(subpart[0:1])
                self.phone = fix_text(subpart[1:])
            elif subpart.startswith(">pm "):
                self.pm_type = fix_text(subpart[4:5])
                self.pm = fix_text(subpart[5:])
            elif subpart.startswith(">pm. "):
                self.pm_type = fix_text(subpart[4:5])
                self.pm = fix_text(subpart[5:])
            elif subpart.startswith(">w "):
                self.type = 'B'
                self.word = fix_text(subpart[3:])
                self.pseudoword = False
            elif subpart.startswith(">w. "):
                self.type = 'B'
                self.word = fix_text(subpart[4:])
                self.pseudoword = False
            elif subpart.startswith("X"):
                if hasattr(self, 'type'):
                    print(self.type, self.type == 'B')
                self.type = getattr(self, 'type', 'B')
                self.word = fix_text(subpart)
                self.pseudoword = True
            elif subpart == "OK":
                self.type = 'E'

    def __repr__(self):
        parts = []
        parts.append(f"type: {self.type}")
        parts.append(f"frame: {self.frame}")
        if self.type != 'E':
            parts.append(f"phone: {self.phone}")
        if 'word' in self.__dict__:
            parts.append(f"word: {self.word}")
        if 'pm_type' in self.__dict__:
            parts.append(f"pm_type: {self.pm_type}")
        if 'pm' in self.__dict__:
            parts.append(f"pm: {self.pm}")
        parts.append(f"sec: {self.seconds}")
        return "FR(" + ", ".join(parts) + ")"

    def get_phone(self):
        if 'pm' in self.__dict__:
            return self.pm
        elif 'phone' in self.__dict__:
            return self.phone
        else:
            return None


class Mix():
    def __init__(self, filepath: str, stringfile=None):
        self.fr = []
        if stringfile is None:
            with open(filepath) as inpf:
                self.read_data(inpf.readlines())
        else:
            self.read_data(stringfile.split("\n"))

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
                self.fr.append(FR(line))
            if line.startswith("Labels: "):
                self.labels = line[8:].strip()
                saw_labels = True
            if saw_labels and line.startswith(" "):
                self.labels += line.strip()

    def check_fr(self) -> bool:
        """
        Simple sanity check: that there were FR lines,
        and that the first was a start type, and
        last was an end type.
        """
        if 'fr' not in self.__dict__:
            return False
        if len(self.fr) == 0:
            return False
        return self.fr[0].type == "B" and self.fr[-1].type == "E"

    def get_times(self, as_frames=False):
        """
        get the times of each phoneme
        """
        if not self.check_fr():
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

    def get_dictionary(self):
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
                phone = fr.get_phone()
                if prev_word != "":
                    if prev_word not in output:
                        output[prev_word] = []
                    output[prev_word].append(current_phones.copy())
                    current_phones.clear()
                prev_word = fr.word
                current_phones.append(phone)
            elif fr.type == "I":
                phone = fr.get_phone()
                current_phones.append(phone)
            else:
                if prev_word not in output:
                    output[prev_word] = []
                output[prev_word].append(current_phones.copy())
                return output
