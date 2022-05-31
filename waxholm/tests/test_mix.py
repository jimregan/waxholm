from waxholm import FR

def test_fr1():
    line = "FR       4481	 #sm	>pm #sm	>w XsmackX	 0.280 sec"
    fr = FR(line)
    print(fr)
