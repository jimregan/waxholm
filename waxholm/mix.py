from .exceptions import FRExpected


def fix_text(text: str) -> str:
    replacements = text.maketrans("{}|\\[]", "äåöÖÄÅ")
    return text.translate(replacements)


class FR:
    def __init__(self, text: str):
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
                self.phone_type = fix_text(subpart[0:2])
                self.phone = fix_text(subpart[1:])
            elif subpart.startswith("#"):
                self.type = 'B'
                self.phone_type = fix_text(subpart[0:2])
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


class Mix():
    def __init__(self, filepath: str):
        self.fr = []
        with open(filepath) as inpf:
            saw_text = False
            saw_phoneme = False
            saw_labels = False
            for line in inpf.readlines():
                if line.startswith("Waxholm dialog."):
                    self.filepath = line[15:].strip()
                if line.startswith("TEXT:"):
                    saw_text = True
                    continue
                if saw_text:
                    self.text = fix_text(line.strip())
                    saw_text = False
                if line.startswith("FR "):
                    if saw_labels:
                        saw_labels = False
                    self.fr.append(FR(line))
                if line.startswith("Labels: "):
                    self.labels = line[8:].strip()
                    saw_labels = True
                if saw_labels and line.startswith(" "):
                    self.labels += line.strip()
