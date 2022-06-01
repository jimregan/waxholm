# -*- coding: utf-8 -*-
from waxholm import FR


def test_fr1():
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


def test_fr2():
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
