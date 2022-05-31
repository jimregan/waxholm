class FRExpected(Exception):
    """Exception to raise when FR line was expected, but not read"""
    def __init__(self, line):
        super().__init__("Unknown line type (does not begin with 'FR'): " + line)
