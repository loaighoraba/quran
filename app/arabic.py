import unicodedata
from difflib import SequenceMatcher

# Not combining marks (Unicode category Mn) but letters, so stripped explicitly: tatweel, and the
# small waw and yeh that Uthmani script writes after a long pronoun ending (بِهِۦ, لَهُۥ). Like the
# dagger alef, the small letters aren't part of the word's written skeleton.
EXTRA_STRIPPED = {"ـ", "ۥ", "ۦ"}


def normalize_arabic(text: str) -> str:
    """Strip diacritics, tatweel and small waw/yeh, and map alef wasla to alef, for search."""
    decomposed = unicodedata.normalize("NFD", text)
    stripped = "".join(
        c for c in decomposed if unicodedata.category(c) != "Mn" and c not in EXTRA_STRIPPED
    )
    return stripped.replace("ٱ", "ا")


DAGGER_ALEF = "\u0670"
# Letters that differ between the scripts only in how the hamza or yeh is written
_LETTER_KEYS = str.maketrans("ٱأإآىةؤئ", "اااايهوي")


def _letter_keys(text: str) -> list[tuple[str, bool]]:
    """(letter, is a dagger alif) for each letter of text; a dagger alif counts as an alef."""
    return [
        ("ا" if c == DAGGER_ALEF else c.translate(_LETTER_KEYS), c == DAGGER_ALEF)
        for c in unicodedata.normalize("NFD", text)
        if unicodedata.category(c) == "Lo" or c == DAGGER_ALEF
    ]


def spell_part_in_simple_script(part: str, word_uthmani: str, word_simple: str | None) -> str:
    """A part of an Uthmani word (a stem) with its dagger alifs spelled as the simple script does.

    The Uthmani script writes many long ā as a dagger alif (ثَلَٰثَ), which the simple script
    spells with an alef (ثَلَاثَ) or leaves out (ذَٰلِكَ -> ذَلِكَ). Which one is read off the
    whole word, by aligning its letters with the simple spelling.
    """
    offset = word_uthmani.find(part)
    if word_simple is None or offset < 0 or DAGGER_ALEF not in part:
        return part
    uthmani = _letter_keys(word_uthmani)
    simple = [key for key, _ in _letter_keys(word_simple)]
    matcher = SequenceMatcher(None, [key for key, _ in uthmani], simple, autojunk=False)
    matched = {
        i for block in matcher.get_matching_blocks() for i in range(block.a, block.a + block.size)
    }
    # Whether each dagger alif of the word is written, in order
    written = [i in matched for i, (_, is_dagger) in enumerate(uthmani) if is_dagger]
    seen = word_uthmani[:offset].count(DAGGER_ALEF)
    spelled = []
    for c in part:
        if c != DAGGER_ALEF:
            spelled.append(c)
        else:
            spelled.append("ا" if written[seen] else "")
            seen += 1
    return "".join(spelled)
