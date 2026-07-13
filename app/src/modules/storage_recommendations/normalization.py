import re
import unicodedata

_QUANTITY_PATTERN = re.compile(
    r'\b\d+([.,]\d+)?\s*(kg|g|gr|ml|l|pcs|pack|bottle|can)\b',
    re.IGNORECASE,
)
_PUNCTUATION_PATTERN = re.compile(r'[^\w\s-]', re.UNICODE)
_SPACES_PATTERN = re.compile(r'\s+')
_STOP_WORDS = {
    'my',
    'fresh',
    'organic',
    'bio',
    'new',
    'small',
    'large',
    'medium',
    'red',
    'green',
    'yellow',
    'white',
    'black',
}


def normalize_storage_name(value: str) -> str:
    text = unicodedata.normalize('NFKC', value).lower()
    text = _QUANTITY_PATTERN.sub(' ', text)
    text = _PUNCTUATION_PATTERN.sub(' ', text)
    text = text.replace('-', ' ')

    words = [word for word in _SPACES_PATTERN.split(text.strip()) if word and word not in _STOP_WORDS]

    return ' '.join(words)
