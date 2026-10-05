import base64
import re
import secrets
import string

_ENV_ASSIGNMENT = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)=(.*)$")


def generate_password(length=32):
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def generate_secret(method: str, nbytes: int = 32) -> str:
    """Generate a local secret. method: 'hex' | 'base64'."""
    if method == "hex":
        return secrets.token_hex(nbytes)
    if method == "base64":
        return base64.b64encode(secrets.token_bytes(nbytes)).decode("ascii")
    raise ValueError(f"Unsupported secret method: {method}")


def read_env_value(env_path: str, key: str) -> str | None:
    """Return the raw value for KEY in a .env file, or None if missing."""
    with open(env_path) as f:
        for line in f:
            match = _ENV_ASSIGNMENT.match(line.rstrip("\n"))
            if match is None or match.group(1) != key:
                continue
            return match.group(2).strip().strip("'\"")
    return None


def set_env_value(env_path: str, key: str, value: str) -> None:
    """Replace KEY=... in place, or append if the key is absent."""
    with open(env_path) as f:
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

    with open(env_path, "w") as f:
        f.writelines(new_lines)


def print_header(title):
    width = 66
    print("\n" + "╔" + "═" * (width - 2) + "╗")
    print(f"║ {title:^{width - 4}} ║")
    print("╚" + "═" * (width - 2) + "╝\n")


def success(msg):
    print(f"✅ {msg}")


def warning(msg):
    print(f"⚠️  {msg}")


def error(msg):
    print(f"❌ {msg}")
