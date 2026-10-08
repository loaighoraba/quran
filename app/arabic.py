import unicodedata

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
