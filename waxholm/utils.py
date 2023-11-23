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


def clean_x_words(words):
    """Removes 'X' words (non-spoken noise markers) from the next

    Args:
        words (List[str]): list of words to clean
    """
    def clean_x_word(word):
        if "XX" in word:
            return ""
        elif word.startswith("X") and word.endswith("X"):
            return ""
        else:
            return word
    return [x for x in words if clean_x_word(x) != ""]


