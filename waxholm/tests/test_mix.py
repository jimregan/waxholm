from waxholm import FR


def test_fr1():
    line = "FR       4481	 #sm	>pm #sm	>w XsmackX	 0.280 sec"
    fr = FR(line)
    assert fr.type == "B"
    assert fr.phone == "sm"
    assert fr.frame == "4481"
    assert 'word' in fr.__dict__
    assert fr.word == "XsmackX"
    assert fr.phone_type == "#"
    assert fr.pm_type == "#"
    print(fr)
