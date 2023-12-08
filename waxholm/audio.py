# Copyright (c) 2023, Jim O'Regan for Språkbanken Tal
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import soundfile as sf
from pathlib import Path


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
    if type(infile) == Path:
        infile = str(infile)
    if type(outfile) == Path:
        outfile = str(outfile)
    data, sr = smp_read_sf(infile)
    write_wav(outfile, data)
