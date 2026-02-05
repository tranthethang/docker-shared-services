import secrets
import string
import sys

def generate_password(length=32):
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

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
