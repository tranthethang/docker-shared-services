import base64
import hashlib
import re
import secrets
import string
import subprocess
from collections.abc import Iterator
from pathlib import Path

_ENV_ASSIGNMENT = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)=(.*)$")

# Any path form the env helpers accept.
StrPath = str | Path


# Special characters that are safe in URLs, shell, .env and compose files.
PASSWORD_SPECIALS = "-_.!*"  # noqa: S105  # character set, not a credential
PASSWORD_MIN_LENGTH = 15


def validate_password_strength(password: str) -> str | None:
    """Return an error message if the password is too weak, else None."""
    if len(password) < PASSWORD_MIN_LENGTH:
        return f"Password must be at least {PASSWORD_MIN_LENGTH} characters."
    if not re.search(r"[a-z]", password):
        return "Password must contain a lowercase letter."
    if not re.search(r"[A-Z]", password):
        return "Password must contain an uppercase letter."
    if not re.search(r"\d", password):
        return "Password must contain a digit."
    if not re.search(r"[^A-Za-z0-9]", password):
        return "Password must contain a special character."
    return None


def generate_password(length: int = 32) -> str:
    length = max(length, PASSWORD_MIN_LENGTH)
    pools = [
        string.ascii_lowercase,
        string.ascii_uppercase,
        string.digits,
        PASSWORD_SPECIALS,
    ]
    alphabet = "".join(pools)
    chars = [secrets.choice(pool) for pool in pools]
    chars += [secrets.choice(alphabet) for _ in range(length - len(chars))]
    secrets.SystemRandom().shuffle(chars)
    # Avoid a leading special char (e.g. "-" parsed as a CLI flag).
    if chars[0] in PASSWORD_SPECIALS:
        idx = next(i for i, c in enumerate(chars) if c not in PASSWORD_SPECIALS)
        chars[0], chars[idx] = chars[idx], chars[0]
    return "".join(chars)


def generate_secret(method: str, nbytes: int = 32, password: str | None = None) -> str:
    """Generate a local secret. method: 'hex' | 'base64' | 'htpasswd'."""
    if method == "hex":
        return secrets.token_hex(nbytes)
    if method == "base64":
        return base64.b64encode(secrets.token_bytes(nbytes)).decode("ascii")
    if method == "htpasswd":
        password = password or generate_password(nbytes)
        salt = secrets.token_hex(4)
        try:
            # Fixed argv, no shell; openssl is resolved from PATH on the host.
            res = subprocess.run(  # noqa: S603
                ["openssl", "passwd", "-apr1", "-salt", salt, "-stdin"],  # noqa: S607
                input=password + "\n",
                capture_output=True,
                text=True,
                check=True,
            )
            return f"admin:{res.stdout.strip().replace('$', '$$')}"
        except Exception:
            # htpasswd {SHA} format is defined as SHA1; Traefik basic auth reads it as such.
            digest = hashlib.sha1(password.encode("utf-8")).digest()  # noqa: S324
            sha1_hash = base64.b64encode(digest).decode("ascii")
            return f"admin:{{SHA}}{sha1_hash}"
    raise ValueError(f"Unsupported secret method: {method}")


def iter_env_assignments(env_path: StrPath) -> Iterator[tuple[str, str]]:
    """Yield (KEY, raw_value) for each assignment line (comments/blank skipped)."""
    with Path(env_path).open() as f:
        for line in f:
            match = _ENV_ASSIGNMENT.match(line.rstrip("\n"))
            if match is None:
                continue
            yield match.group(1), match.group(2)


def read_env_value(env_path: StrPath, key: str) -> str | None:
    """Return the raw value for KEY in a .env file, or None if missing."""
    for name, value in iter_env_assignments(env_path):
        if name == key:
            return value.strip().strip("'\"")
    return None


def set_env_value(env_path: StrPath, key: str, value: str) -> None:
    """Replace KEY=... in place, or append if the key is absent."""
    with Path(env_path).open() as f:
        lines = f.readlines()

    replaced = False
    new_lines: list[str] = []
    for line in lines:
        match = _ENV_ASSIGNMENT.match(line.rstrip("\n"))
        if match is not None and match.group(1) == key:
            new_lines.append(f"{key}={value}\n")
            replaced = True
            continue
        new_lines.append(line if line.endswith("\n") else f"{line}\n")

    if not replaced:
        if new_lines and not new_lines[-1].endswith("\n"):
            new_lines[-1] += "\n"
        new_lines.append(f"{key}={value}\n")

    with Path(env_path).open("w") as f:
        f.writelines(new_lines)


def print_header(title: str) -> None:
    width = 66
    print("\n" + "╔" + "═" * (width - 2) + "╗")
    print(f"║ {title:^{width - 4}} ║")
    print("╚" + "═" * (width - 2) + "╝\n")


def success(msg: str) -> None:
    print(f"✅ {msg}")


def warning(msg: str) -> None:
    print(f"⚠️  {msg}")


def error(msg: str) -> None:
    print(f"❌ {msg}")
