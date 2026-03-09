"""Dangerous command detection for aish."""

from __future__ import annotations
import re
from enum import Enum


class RiskLevel(Enum):
    ALLOW = "allow"
    WARN = "warn"
    DENY = "deny"


# Patterns that DENY execution outright
DENY_PATTERNS = [
    r":\s*\(\s*\)\s*\{",  # fork bomb: :(){
    r"\bmkfs\b",  # format filesystem
    r"\bfdisk\b.*--wipe",  # disk wipe
    r"dd\s+if=.*of=/dev/(sd|hd|nvme|disk)",  # dd to raw disk
    r">\s*/dev/(sd[a-z]|hd[a-z]|nvme\d)",  # redirect to raw disk
    r"shred\s+.*(/dev/|/boot/)",  # shred critical paths
]

# Patterns that WARN and require explicit confirmation
WARN_PATTERNS = [
    r"\brm\s+(-[rfRF]+\s+|-[rfRF]+$)",  # rm with -r or -f flags
    r"\brm\s+-[a-zA-Z]*[rf][a-zA-Z]*",  # rm with r or f anywhere in flags
    r"\bsudo\b",  # sudo usage
    r"chmod\s+(777|[0-7]{3})\s+",  # chmod
    r"\|\s*(sh|bash|zsh|fish)\b",  # pipe to shell
    r"\bwget\b.*\|\s*(sh|bash)",  # wget | bash
    r"\bcurl\b.*\|\s*(sh|bash)",  # curl | bash
    r"\bdd\b.*\bof=",  # dd with output file
    r">\s*/etc/",  # redirect to /etc/
    r">\s*/usr/",  # redirect to /usr/
    r">\s*/boot/",  # redirect to /boot/
    r"\bchown\b.*-[Rr]",  # recursive chown
    r"\bkillall\b",  # killall
    r"\bpkill\b",  # pkill
    r"\bsystemctl\b.*(stop|disable|mask)",  # stop system services
    r"\buseradd\b|\buserdel\b|\busermod\b",  # user management
]


def check_command(command: str) -> tuple[RiskLevel, list[str]]:
    """
    Check a command for dangerous patterns.
    Returns (RiskLevel, list_of_matched_patterns).
    """
    matches: list[str] = []

    for pattern in DENY_PATTERNS:
        if re.search(pattern, command, re.IGNORECASE):
            matches.append(pattern)
            return RiskLevel.DENY, matches

    for pattern in WARN_PATTERNS:
        if re.search(pattern, command, re.IGNORECASE):
            matches.append(pattern)

    if matches:
        return RiskLevel.WARN, matches

    return RiskLevel.ALLOW, []


def is_dangerous(command: str) -> bool:
    """Returns True if the command is WARN or DENY level."""
    level, _ = check_command(command)
    return level != RiskLevel.ALLOW
