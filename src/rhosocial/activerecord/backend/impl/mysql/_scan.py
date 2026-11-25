# src/rhosocial/activerecord/backend/impl/mysql/_scan.py
"""Character scanning for MySQL's read-direction parsers.

``src`` is not allowed to import :mod:`re`: a server-reported spelling is read
by walking its characters, not by matching a pattern against it. This module
holds the scanning helpers that the introspection parsers share.

Every helper reproduces the exact semantics of the pattern it replaced, so
strings ``information_schema`` reports parse to the same values they did
before:

* word characters follow ``re``'s Unicode notion of ``\\b`` -- a character is
  a word character when ``str.isalnum()`` is true or it is an underscore;
* digits are Unicode decimal digits, which is what ``\\d`` matched;
* blanks are ``str.isspace()`` characters, which is what ``\\s`` matched.
"""

from __future__ import annotations

from typing import List, Optional, Sequence, Tuple


def is_word_char(ch: str) -> bool:
    """Whether ``ch`` belongs to a word run, matching ``re``'s ``\\b`` boundary."""
    return ch == "_" or ch.isalnum()


def leading_word(text: str) -> str:
    """Return the longest word-character run at the start of ``text``.

    An empty string means the text does not start with a word character, so
    no leading word exists (the case a ``^(?:WORD)\\b`` pattern rejected).
    """
    index = 0
    length = len(text)
    while index < length and is_word_char(text[index]):
        index += 1
    return text[:index]


def starts_with_word(text: str, words: Sequence[str]) -> bool:
    """Whether ``text`` begins with one of ``words`` as a whole leading word.

    ``words`` are spelled in upper case and compared case-insensitively, as
    the case-insensitive prefix matchers they replace did. The whole leading
    word has to match: ``BITS`` does not begin with ``BIT``, and ``INTEGER``
    is not read as ``INT`` followed by a word boundary.
    """
    head = leading_word(text)
    if not head:
        return False
    return head.upper() in words


def leading_upper_run(text: str) -> str:
    """Return the run of ASCII upper-case letters at the start of ``text``.

    An empty string means the text does not start with an upper-case letter;
    callers fall back to the whole text in that case.
    """
    index = 0
    length = len(text)
    while index < length and "A" <= text[index] <= "Z":
        index += 1
    return text[:index]


def _decimal_run(text: str, index: int) -> Tuple[int, str]:
    """Read a maximal decimal-digit run starting at ``index``.

    Returns the index just past the run and the run itself.
    """
    length = len(text)
    start = index
    while index < length and text[index].isdecimal():
        index += 1
    return index, text[start:index]


def digit_runs(text: str) -> List[str]:
    """Return every maximal decimal-digit run in ``text``, left to right."""
    runs: List[str] = []
    index = 0
    length = len(text)
    while index < length:
        if text[index].isdecimal():
            index, run = _decimal_run(text, index)
            runs.append(run)
        else:
            index += 1
    return runs


def first_digit_run(text: str) -> Optional[str]:
    """Return the first maximal decimal-digit run in ``text``, or ``None``."""
    index = 0
    length = len(text)
    while index < length:
        if text[index].isdecimal():
            _, run = _decimal_run(text, index)
            return run
        index += 1
    return None


def _skip_blanks(text: str, index: int) -> int:
    """Return the index of the first non-blank at or after ``index``."""
    length = len(text)
    while index < length and text[index].isspace():
        index += 1
    return index


def parenthesized_digits(text: str, allow_blanks: bool = False) -> Optional[str]:
    """Return the digits inside the first parenthesised group holding only digits.

    With ``allow_blanks`` the group may be padded with blanks, so ``BIGINT( 20 )``
    reports ``"20"``; without it the digits must sit flush against both
    parentheses, so ``VARCHAR(20)`` reports ``"20"`` and ``VARCHAR( 20 )``
    reports ``None``. ``None`` means no such group exists.
    """
    length = len(text)
    index = 0
    while index < length:
        if text[index] != "(":
            index += 1
            continue
        cursor = index + 1
        if allow_blanks:
            cursor = _skip_blanks(text, cursor)
        if cursor < length and text[cursor].isdecimal():
            end, digits = _decimal_run(text, cursor)
            if allow_blanks:
                end = _skip_blanks(text, end)
            if end < length and text[end] == ")":
                return digits
        index += 1
    return None


def quoted_values(text: str) -> List[str]:
    """Return the contents of each ``'...'`` literal in ``text``, left to right.

    Matches are read as a quoted literal followed by the next quote, so an
    unquoted apostrophe inside the literal ends it exactly where the pattern
    it replaces did. An unterminated quote yields no value and stops the scan,
    because no later quote could close it either.
    """
    values: List[str] = []
    index = 0
    length = len(text)
    while index < length:
        if text[index] != "'":
            index += 1
            continue
        closing = text.find("'", index + 1)
        if closing < 0:
            break
        values.append(text[index + 1 : closing])
        index = closing + 1
    return values


def _run_after_blanks(text: str, index: int, is_run_char) -> Optional[str]:
    """Read a run of ``is_run_char`` characters after one or more blanks."""
    length = len(text)
    if index >= length or not text[index].isspace():
        return None
    index = _skip_blanks(text, index)
    start = index
    while index < length and is_run_char(text[index]):
        index += 1
    if index == start:
        return None
    return text[start:index]


def _run_after_marker(text: str, marker: Sequence[str], is_run_char) -> Optional[str]:
    """Return the run that follows ``marker`` words separated by blanks.

    Each occurrence of the first marker word is tried in turn, so a near-miss
    (``CHARACTER SETS``) does not hide a genuine later match, exactly as a
    pattern search would move on to the next occurrence.
    """
    first = marker[0]
    length = len(text)
    start = 0
    while True:
        found = text.find(first, start)
        if found < 0:
            return None
        cursor = found + len(first)
        matched = True
        for word in marker[1:]:
            if cursor >= length or not text[cursor].isspace():
                matched = False
                break
            cursor = _skip_blanks(text, cursor)
            if not text.startswith(word, cursor):
                matched = False
                break
            cursor += len(word)
        if matched:
            run = _run_after_blanks(text, cursor, is_run_char)
            if run is not None:
                return run
        start = found + 1


def word_after(text: str, *marker: str) -> Optional[str]:
    """Return the first word run preceded by ``marker`` words plus blanks.

    With ``marker=("CHARACTER", "SET")`` this reads the character set out of
    ``ENUM('a') CHARACTER SET utf8mb4``; a single word marker reads the
    collation out of ``... COLLATE utf8mb4_bin``. ``None`` means the marker
    never appears followed by a blank and a word.
    """
    return _run_after_marker(text, marker, is_word_char)


def digits_after(text: str, *marker: str) -> Optional[str]:
    """Return the first digit run preceded by ``marker`` words plus blanks.

    Reads the SRID out of ``POINT SRID 4326``. ``None`` means no marker is
    followed by a blank and a digit run.
    """
    return _run_after_marker(text, marker, str.isdecimal)
