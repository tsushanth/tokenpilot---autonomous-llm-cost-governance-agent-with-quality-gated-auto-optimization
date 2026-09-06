"""Generates a cheaper candidate for a Task: a compressed prompt routed to the
cheap model tier. This is deliberately simple (regex filler-stripping) — the
point of the MVP is the quality gate around the optimization, not a
state-of-the-art compressor."""

import re

from tokenpilot.providers import CHEAP_MODEL

# (pattern, replacement) pairs applied in order. Case-insensitive; each strips
# a filler word/phrase that carries no instruction-following signal.
_FILLER_REPLACEMENTS = [
    (r"(?i)\bin order to\b", "to"),
    (r"(?i)\bi would like you to\b", ""),
    (r"(?i)\bcould you please\b", ""),
    (r"(?i)\bplease\b", ""),
    (r"(?i)\bkindly\b", ""),
    (r"(?i)\bjust\b", ""),
    (r"(?i)\bsimply\b", ""),
    (r"(?i)\bbasically\b", ""),
    (r"(?i)\bactually\b", ""),
    (r"(?i)\breally\b", ""),
    (r"(?i)\bvery\b", ""),
    (r"(?i)\bcarefully and politely\b", ""),
    (r"(?i)\bcarefully\b", ""),
    (r"(?i)\bpolitely\b", ""),
]


def compress_prompt(template: str) -> str:
    text = template
    for pattern, replacement in _FILLER_REPLACEMENTS:
        text = re.sub(pattern, replacement, text)
    # Collapse whitespace left behind by the deletions above.
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" +\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r" {2,}", " ", text)
    return text.strip()


def generate_candidate(task) -> dict:
    """Returns {"prompt_template": ..., "model": ...} — a cheaper variant of
    the task's baseline, always routed to the cheap tier and with filler
    stripped from the prompt template."""
    return {
        "prompt_template": compress_prompt(task.prompt_template),
        "model": CHEAP_MODEL,
    }
