from enum import StrEnum
from typing import Literal

from pydantic import BaseModel


class CountBy(StrEnum):
    # Written word, with the vocative يا split off: مريم matches يمريم but not ومريم
    word = "word"
    # Word without prefixes and suffixes: مريم matches يمريم and ومريم
    stem = "stem"
    # Dictionary form: قال matches قالوا, يقول, قل
    lemma = "lemma"
    # Root letters: رحم matches رحمن, رحيم, رحمة
    root = "root"


class Summary(BaseModel):
    ayas: int
    # The vocative يا counted as its own word, as in the simple script
    words: int
    # One word per Uthmani-script word (يمريم is one word)
    words_uthmani: int
    roots: int
    lemmas: int


class Frequency(BaseModel):
    value: str
    count: int


class Count(BaseModel):
    by: CountBy
    query: str
    count: int
    # word and stem: the diacritized forms matched; lemma: the lemmas matched; root: its lemmas
    breakdown: list[Frequency]


class SurahOut(BaseModel):
    id: int
    name_arabic: str
    name_transliterated: str
    name_english: str
    revelation_type: Literal["meccan", "medinan"]
    aya_count: int
