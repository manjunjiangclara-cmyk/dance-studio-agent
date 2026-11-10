"""Local pseudonymization of known student identity and email addresses before model calls.

Mappings never leave this process. This targets names, email addresses and the student ID;
other identifying details in free text need separate detection rules.
"""

import json
import re
import unicodedata
from uuid import UUID

EMAIL = re.compile(r"[\w.!#$%&'*+/=?^`{|}~\-]+@[\w\-]+(?:\.[\w\-]+)+", re.UNICODE)
UNKNOWN_GREETING = re.compile(
    r"(?im)^(\s*(?:hi|hello|dear|hey)\s+)(?:new enquirer|new|enquirer)(?=[!,\.\s]|$)"
)


def normalize_unknown_greeting(body: str, student: dict) -> str:
    if str(student.get("name") or "").strip().casefold() != "new enquirer":
        return body
    return UNKNOWN_GREETING.sub(r"\1there", body)


def _normalized(value: str) -> str:
    return unicodedata.normalize("NFC", value)


class StudentPrivacy:
    def __init__(self, student: dict):
        self.originals: dict[str, str] = {}
        self.aliases: dict[str, str] = {}
        self.email_tokens: dict[str, str] = {}
        name = _normalized(str(student.get("name") or "")).strip()
        if name:
            self._alias(name, "[STUDENT_NAME]")
            parts = list(dict.fromkeys([*name.split(), *re.findall(r"[^\W\d_]+", name)]))
            for index, part in enumerate(parts, 1):
                if part and part.casefold() not in self.aliases:
                    self._alias(part, f"[STUDENT_NAME_{index}]")
        student_id = str(student.get("id") or "")
        if student_id:
            self._alias(student_id, "[STUDENT_ID]")
        email = _normalized(str(student.get("email") or ""))
        if email:
            self.email_tokens[email.casefold()] = "[STUDENT_EMAIL]"
            self._alias(email, "[STUDENT_EMAIL]")
        alternatives = sorted(
            set(self.aliases) | {self.originals[token] for token in self.aliases.values()},
            key=len,
            reverse=True,
        )
        self.identity_pattern = (
            re.compile(
                "|".join(
                    re.escape(a)
                    if self.aliases[a.casefold()] in {"[STUDENT_ID]", "[STUDENT_EMAIL]"}
                    or any(
                        unicodedata.name(char, "").startswith(
                            ("CJK", "HIRAGANA", "KATAKANA", "HANGUL", "THAI")
                        )
                        for char in a
                    )
                    else r"(?<!\w)" + re.escape(a) + r"(?!\w)"
                    for a in alternatives
                ),
                re.I,
            )
            if alternatives
            else None
        )

    def _alias(self, original: str, token: str):
        self.aliases[original.casefold()] = token
        self.originals[token] = original

    def _email(self, match):
        address = match.group()
        key = address.casefold()
        if key not in self.email_tokens:
            token = f"[EMAIL_{len(self.email_tokens) + 1}]"
            self.email_tokens[key] = token
            self.originals[token] = address
        return self.email_tokens[key]

    def _text(self, text: str) -> str:
        text = _normalized(text)
        # Tool arguments/results can be JSON encoded inside an outer request string.
        if text.lstrip().startswith(("{", "[")):
            try:
                nested = json.loads(text)
            except ValueError:
                pass
            else:
                if isinstance(nested, (dict, list)):
                    return json.dumps(self.redact(nested), ensure_ascii=False)
        text = EMAIL.sub(self._email, text)
        if self.identity_pattern:
            text = self.identity_pattern.sub(
                lambda match: self.aliases.get(match.group().casefold(), "[STUDENT_NAME]"),
                text,
            )
        return text

    def redact(self, value):
        if isinstance(value, (str, UUID)):
            return self._text(str(value))
        if isinstance(value, dict):
            return {self._text(str(key)): self.redact(item) for key, item in value.items()}
        if isinstance(value, list):
            return [self.redact(item) for item in value]
        return value

    def transcript(self, items: list[dict]) -> list[dict]:
        safe = []
        for item in items:
            # Encrypted reasoning is an opaque provider-generated replay token, not plain text.
            if item.get("type") == "reasoning" and "encrypted_content" in item:
                safe.append(
                    {
                        **self.redact({k: v for k, v in item.items() if k != "encrypted_content"}),
                        "encrypted_content": item["encrypted_content"],
                    }
                )
            else:
                safe.append(self.redact(item))
        return safe

    def restore(self, value):
        if isinstance(value, str):
            if not self.originals:
                return value
            pattern = "|".join(re.escape(token) for token in self.originals)
            return re.sub(pattern, lambda match: self.originals[match.group()], value)
        if isinstance(value, dict):
            return {self.restore(key): self.restore(item) for key, item in value.items()}
        if isinstance(value, list):
            return [self.restore(item) for item in value]
        return value
