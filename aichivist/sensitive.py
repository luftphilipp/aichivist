"""Secrets in a document's text: access tokens, private keys, recovery codes, card-like numbers.

Names the kind of secret, never the secret itself, so a warning can be shown and logged safely.
Built for screenshots and notes that end up in Downloads; a hint for the person, not a scanner.
"""
import re
from typing import List

ACCESS_TOKEN, PRIVATE_KEY, RECOVERY = "access token", "private key", "recovery codes"
ACCOUNT_KEY, PASSWORD, CARD, PHRASE = "account key", "password", "card-like number", "wallet recovery phrase"
ORDER = [ACCESS_TOKEN, PRIVATE_KEY, RECOVERY, ACCOUNT_KEY, PHRASE, PASSWORD, CARD]

PATTERNS = [  # (kind, pattern) – shapes of secrets
    (ACCESS_TOKEN, re.compile(r"\beyJ[\w-]{8,}\.[\w-]{8,}")),  # JSON Web Token (OCR may swap letters: \w is Unicode)
    (ACCESS_TOKEN, re.compile(r"\b(?:ghp_|gho_|github_pat_|glpat-|xox[bpa]-|pypi-|sk-(?:ant-|proj-)?)[\w-]{16,}")),
    (ACCESS_TOKEN, re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    (PRIVATE_KEY, re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
]
LABELS = [  # (kind, words that announce a secret on screen or paper)
    (ACCESS_TOKEN, r"api[ -]?(?:key|token|schlüssel)|access[ -]token|zugriffstoken|bearer token|client secret"),
    (RECOVERY, r"recovery codes?|wiederherstellungscodes?|backup codes?|notfallcodes?"),
    (ACCOUNT_KEY, r"account key|kontoschlüssel|secret key|geheimer schlüssel"),
    (PHRASE, r"seed phrase|recovery phrase|wiederherstellungsphrase"),
    (PASSWORD, r"(?:password|passwort|kennwort)\s*[:=]\s*\S"),
]
LABEL_PATTERNS = [(kind, re.compile(rf"(?<!\w)(?:{words})", re.IGNORECASE)) for kind, words in LABELS]
CARD_NUMBER = re.compile(r"(?<![\w-])\d{4}([ -]?)\d{4}\1\d{4}\1\d{4}(?![ -]?\d)")
LONG_CODE = re.compile(r"[\w-]{24,}")
HIDDEN = "[hidden]"


def _luhn(digits: str) -> bool:
    total = 0
    for i, ch in enumerate(reversed(digits)):
        n = int(ch) * (2 if i % 2 else 1)
        total += n - 9 if n > 9 else n
    return total % 10 == 0


def find(text: str) -> List[str]:
    """Kinds of secrets in the text, each once, in a stable order."""
    found = {kind for kind, pattern in PATTERNS + LABEL_PATTERNS if pattern.search(text)}
    if any(_luhn(re.sub(r"\D", "", m.group(0))) for m in CARD_NUMBER.finditer(text)):
        found.add(CARD)
    return [kind for kind in ORDER if kind in found]


def _random_looking(word: str) -> bool:
    return any(c.isdigit() for c in word) and any(c.isalpha() for c in word)


def redact(text: str) -> str:
    """The text with tokens, keys, long codes and card-like numbers replaced by [hidden]."""
    for _, pattern in PATTERNS:
        text = pattern.sub(HIDDEN, text)
    text = CARD_NUMBER.sub(HIDDEN, text)
    return LONG_CODE.sub(lambda m: HIDDEN if _random_looking(m.group(0)) else m.group(0), text)
