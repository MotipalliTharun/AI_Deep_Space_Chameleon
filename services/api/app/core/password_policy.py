"""
Password rules, following NIST SP 800-63B: favour length, block known-bad
passwords, no forced composition rules or rotation.
"""

MIN_LENGTH = 12
MAX_LENGTH = 128

# Small built-in deny list; swap for a breached-password (HIBP k-anonymity) check later.
_COMMON = frozenset(
    {
        "password1234",
        "passwordpassword",
        "123456789012",
        "qwertyuiopas",
        "letmeinletmein",
        "welcome12345",
        "adminadmin123",
        "iloveyou1234",
        "changeme1234",
        "chameleon123",
    }
)


def password_problems(password: str, email: str = "") -> list[str]:
    problems: list[str] = []
    if len(password) < MIN_LENGTH:
        problems.append(f"must be at least {MIN_LENGTH} characters")
    if len(password) > MAX_LENGTH:
        problems.append(f"must be at most {MAX_LENGTH} characters")
    lowered = password.lower()
    if lowered in _COMMON or len(set(password)) < 4:
        problems.append("is too common or repetitive")
    local_part = email.split("@", 1)[0].lower()
    if len(local_part) >= 4 and local_part in lowered:
        problems.append("must not contain your email name")
    return problems
