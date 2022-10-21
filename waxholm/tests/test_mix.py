from waxholm import Mix


SAMPLE1 = """\
CORRECTED: OK jesper    Jesper Hogberg Thu Jun 22 16:32:23 EET 1995
AUTOLABEL: jesper    Jesper H|gberg Tue May 31 20:22:51 EET 1994
DATA BANK MATERIAL:  file:/u/wax/data/scenes/fp2060/fp2060.1.05.smp.mix
Digital recording in quiet room, No preemph, 16000 kHz, December 1992

Waxholm dialog. /u/wax/data/scenes/fp2060/fp2060.1.05.smp
WIZARD:  jesper    Jesper H|gberg Fri Mar 25 12:22:42 MET 1994
TEXT:
jag vill }ka 17 och 45 .
PHONEME:   J'A:G+ V'IL+ "]:K'A  SJ"UT']N  ']:+ F\\42TIF'EM.


CT 1
Labels:  J'A: V'IL "]:KkA SJ"UTt]N ']Kk F\\42TtIF'EMv
 .
FR       4196	 #J	>pm #J	>w jag	 0.262 sec
FR       5638	 $'A:	>pm $'A:	 0.352 sec
FR       8341	 $G	>pm $G	 0.521 sec
FR       8341	 $g	>pm $g	 0.521 sec
FR       8341	 #V	>pm #V	>w vill	 0.521 sec
FR       9270	 $'I	>pm $'I	 0.579 sec
FR       9586	 $L	>pm $L+	 0.599 sec
FR      10436	 #"]:	>pm #"]:	>w }ka	 0.652 sec
FR      12676	 $K	>pm $K	 0.792 sec
FR      13727	 $k	>pm $k	 0.858 sec
FR      13975	 $A	>pm $A	 0.873 sec
FR      15165	 #SJ	>pm #SJ	>w 17	 0.948 sec
FR      16891	 $"U	>pm $"U	 1.056 sec
FR      18185	 $T	>pm $T	 1.137 sec
FR      20227	 $t	>pm $t	 1.264 sec
FR      20565	 $]	>pm $]	 1.285 sec
FR      21336	 $N	>pm $N	 1.333 sec
FR      21827	 #']	>pm #']	>w och	 1.364 sec
FR      23007	 $K	>pm $K	 1.438 sec
FR      23771	 $k	>pm $k	 1.486 sec
FR      24044	 #F	>pm #F	>w 45	 1.503 sec
FR      25048	 $\\4	>pm $\\4	 1.565 sec
FR      26004	 $2T	>pm $2T	 1.625 sec
FR      26995	 $2t	>pm $2t		1.687 sec
FR      27269	 $I	>pm $I	 1.704 sec
FR      27862	 $F	>pm $F	 1.741 sec
FR      29741	 $'E	>pm $'E	 1.859 sec
FR      32233	 $M	>pm $M	 2.014 sec
FR      34326	 $v	 2.145 sec
FR      35570	 #.	>pm #.	>w .	 2.223 sec
FR      36001	 OK	 2.250 sec
"""


def test_mix_read():
    mix = Mix(filepath="", stringfile=SAMPLE1)
    assert mix.text == "jag vill åka 17 och 45 ."


def test_mix_gettimes():
    mix = Mix(filepath="", stringfile=SAMPLE1)
    times = mix.get_times()
    assert times[0] == 0.262
    assert times[-1] == 2.25


def test_mix_gettimes_asframes():
    mix = Mix(filepath="", stringfile=SAMPLE1)
    times = mix.get_times(as_frames=True)
    assert times[0] == 4196
    assert times[-1] == 36001


def test_mix_phoneme_string():
    mix = Mix(filepath="", stringfile=SAMPLE1)
    assert mix.phoneme == "J'A:G+ V'IL+ \"Å:K'A  SJ\"UT'ÅN  'Å:+ FÖ42TIF'EM."


def test_get_dictionary():
    mix = Mix(filepath="", stringfile=SAMPLE1)
    dictionary = mix.get_dictionary()
    assert len(dictionary.keys()) == 7
    assert "vill" in dictionary.keys()
    assert dictionary["vill"] == [["V", "ˈI", "L+"]]


def test_get_time_pairs_seconds():
    mix = Mix(filepath="", stringfile=SAMPLE1)
    pairs = mix.get_time_pairs()
    assert pairs[0] == (0.262, 0.352)
    assert pairs[-1] == (2.223, 2.25)


def test_get_time_pairs_frames():
    mix = Mix(filepath="", stringfile=SAMPLE1)
    pairs = mix.get_time_pairs(as_frames=True)
    assert pairs[0] == (4196, 5638)
    assert pairs[-1] == (35570, 36001)

def test_get_phone_label_tuples():
    mix = Mix(filepath="", stringfile=SAMPLE1)
    tuples = mix.get_phone_label_tuples(as_frames=True)
    assert tuples[0] == (4196, 5638, "J")
    assert tuples[-1] == (35570, 36001, ".")

def test_get_merged_plosives():
    mix = Mix(filepath="", stringfile=SAMPLE1)
    assert len(mix.fr) == 31
    merged = mix.get_merged_plosives(prune_empty=False)
    assert len(merged) == 24

def test_merge_plosives():
    mix = Mix(filepath="", stringfile=SAMPLE1)
    assert "orig_fr" not in mix.__dict__
    assert len(mix.fr) == 31
    mix.merge_plosives()
    assert "orig_fr" in mix.__dict__
    assert len(mix.fr) == 26
