import soundfile as sf


def smp_headers(filename: str):
    with open(filename, "rb") as f:
        f.seek(0)
        raw_headers = f.read(1024)
        raw_headers = raw_headers.rstrip(b'\x00')
        asc_headers = raw_headers.decode("ascii")
        asc_headers.rstrip('\x00')
        tmp = [a for a in asc_headers.split("\r\n")]
        back = -1
        while abs(back) > len(tmp) + 1:
            if tmp[back] == '=':
                break
            back -= 1
        tmp = tmp[0:back-1]
        return dict(a.split("=") for a in tmp)


def smp_read_sf(filename: str):
    headers = smp_headers(filename)
    if headers["msb"] == "last":
        ENDIAN = "LITTLE"
    else:
        ENDIAN = "BIG"

    data, sr = sf.read(filename, channels=int(headers["nchans"]),
                       samplerate=16000, endian=ENDIAN, start=512,
                       dtype="int16", format="RAW", subtype="PCM_16")
    return (data, sr)


def write_wav(filename, arr):
    import wave

    with wave.open(filename, "w") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(16000)
        f.writeframes(arr)


def smp_to_wav(infile, outfile):
    data, sr = smp_read_sf(infile)
    write_wav(outfile, data)
