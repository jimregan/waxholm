class FRExpected(Exception):
    """Exception to raise when FR line was expected, but not read"""
    def __init__(self, line):
        msg = "Unknown line type (does not begin with 'FR'): "
        super().__init__(msg + line)
