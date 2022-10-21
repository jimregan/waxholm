# -*- coding: utf-8 -*-
from waxholm import FR
from waxholm.mix import merge_frs


def test_fr_begin1():
    line = "FR       4481	 #sm	>pm #sm	>w XsmackX	 0.280 sec"
    fr = FR(line)
    assert 'type' in fr.__dict__
    assert fr.type == "B"
    assert 'phone' in fr.__dict__
    assert fr.phone == "sm"
    assert 'frame' in fr.__dict__
    assert fr.frame == "4481"
    assert 'word' in fr.__dict__
    assert fr.word == "XsmackX"
    assert 'phone_type' in fr.__dict__
    assert fr.phone_type == "#"
    assert 'pm_type' in fr.__dict__
    assert fr.pm_type == "#"
    assert 'pm' in fr.__dict__
    assert fr.pm == "sm"
    assert 'seconds' in fr.__dict__
    assert fr.seconds == "0.280"


def test_fr_begin2():
    line = "FR       6671	 #I	>pm #I	>w ikv{ll	 0.417 sec"
    fr = FR(line)
    assert 'type' in fr.__dict__
    assert fr.type == "B"
    assert 'phone' in fr.__dict__
    assert fr.phone == "I"
    assert 'frame' in fr.__dict__
    assert fr.frame == "6671"
    assert 'word' in fr.__dict__
    assert fr.word == "ikväll"
    assert 'phone_type' in fr.__dict__
    assert fr.phone_type == "#"
    assert 'pm_type' in fr.__dict__
    assert fr.pm_type == "#"
    assert 'pm' in fr.__dict__
    assert fr.pm == "I"
    assert 'seconds' in fr.__dict__
    assert fr.seconds == "0.417"


def test_fr_inner1():
    line = "FR      10256	 $'[	>pm $'[	 0.641 sec"
    fr = FR(line)
    assert 'type' in fr.__dict__
    assert fr.type == "I"
    assert 'phone' in fr.__dict__
    assert fr.phone == "'Ä"
    assert 'frame' in fr.__dict__
    assert fr.frame == "10256"
    assert 'word' not in fr.__dict__
    assert 'phone_type' in fr.__dict__
    assert fr.phone_type == "$"
    assert 'pm_type' in fr.__dict__
    assert fr.pm_type == "$"
    assert 'pm' in fr.__dict__
    assert fr.pm == "'Ä"
    assert 'seconds' in fr.__dict__
    assert fr.seconds == "0.641"


def test_fr_end1():
    line = "FR      15241	 OK	 0.952 sec"
    fr = FR(line)
    assert 'type' in fr.__dict__
    assert fr.type == "E"
    assert 'phone' not in fr.__dict__
    assert 'frame' in fr.__dict__
    assert fr.frame == "15241"
    assert 'word' not in fr.__dict__
    assert 'phone_type' not in fr.__dict__
    assert 'pm_type' not in fr.__dict__
    assert 'pm' not in fr.__dict__
    assert 'seconds' in fr.__dict__
    assert fr.seconds == "0.952"


def test_fr_broken_inner1():
    line = "FR      34326	 $v	 2.145 sec"
    fr = FR(line)
    assert 'type' in fr.__dict__
    assert fr.type == "I"
    assert 'phone' in fr.__dict__
    assert fr.phone == "v"
    assert 'frame' in fr.__dict__
    assert fr.frame == "34326"
    assert 'word' not in fr.__dict__
    assert 'phone_type' in fr.__dict__
    assert fr.phone_type == "$"
    assert 'pm_type' not in fr.__dict__
    assert 'pm' not in fr.__dict__
    assert 'seconds' in fr.__dict__
    assert fr.seconds == "2.145"


def test_merge_frs():
    fr1 = FR(text="FR       8341	 $G	>pm $G	 0.521 sec")
    fr2 = FR(text="FR       8341	 $g	>pm $g	 0.521 sec")
    merge = merge_frs(fr1, fr2)
    assert merge.get_phone() == "g"
    fr1 = FR(text="FR       8341	 $g	>pm $g	 0.521 sec")
    fr2 = FR(text="FR       8341	 #V	>pm #V	>w vill	 0.521 sec")
    merge = merge_frs(fr1, fr2)
    assert merge is None
