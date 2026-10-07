import unicodedata


def normalize_arabic(text: str) -> str:
    """Strip diacritics and tatweel, and map alef wasla to alef, for comparison and search."""
    decomposed = unicodedata.normalize("NFD", text)
    stripped = "".join(c for c in decomposed if unicodedata.category(c) != "Mn" and c != "ـ")
    return stripped.replace("ٱ", "ا")
