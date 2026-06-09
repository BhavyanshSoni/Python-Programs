import os
import json
import getpass
import base64
import hashlib
import hmac
import logging
import secrets
import string
import time
from time import sleep
from cryptography.fernet import Fernet, InvalidToken
from typing import Any, Dict, Optional, Tuple

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
USERS_FILE = os.path.join(BASE_DIR, "users.json")
SECURITY_LOG_FILE = os.path.join(BASE_DIR, "security.log")

MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_SECONDS = 60

# Master-key protection
MASTER_KEY_META_VERSION = 1
MASTER_KEY_PBKDF2_ITERATIONS = 300_000
MASTER_KEY_SALT_LEN = 16

# Encryption key protection (for the password vault)
VAULT_VERSION = 2
VAULT_ENC_PBKDF2_ITERATIONS = 400_000
VAULT_ENC_SALT_LEN = 16

PASSWORD_VAULT_FILE_FMT = "passwords_{username}.json"
MASTER_KEY_LEGACY_TXT_FMT = "{username}_key.txt"
MASTER_KEY_META_JSON_FMT = "{username}_masterkey.json"

# Best-effort security logging (never logs secrets)
logger = logging.getLogger("smart_password_saver_security")
try:
    if not logger.handlers:
        handler = logging.FileHandler(SECURITY_LOG_FILE, encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        logger.addHandler(handler)
    logger.setLevel(logging.INFO)
except Exception:
    # Logging must not break program execution.
    logger = logging.getLogger("null")

# ---------------- UI ---------------- #
def s(txt, delay=0.03):
    for i in txt:
        print(i, end='', flush=True)
        sleep(delay)
    print()

# ---------------- UTIL / IO ---------------- #
def _b64encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii")

def _b64decode(b64: str) -> bytes:
    return base64.urlsafe_b64decode(b64.encode("ascii"))

def _atomic_write_json(path: str, data: Any) -> None:
    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)
    os.replace(tmp, path)

def _safe_load_json(path: str, default: Any) -> Any:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return default
    except json.JSONDecodeError:
        logger.warning("JSON decode failed for %s", path)
        s("Storage file is corrupted. Please check or reset it.")
        return default
    except OSError:
        logger.exception("Failed reading %s", path)
        s("Could not read a required file. Check permissions.")
        return default

# ---------------- ENCRYPTION ---------------- #
def _pbkdf2_derive(key_material: str, salt: bytes, iterations: int, dklen: int = 32) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", key_material.encode("utf-8"), salt, iterations, dklen=dklen)

def get_legacy_cipher(master_key: str) -> Fernet:
    """
    Legacy cipher compatibility:
    Old versions derived Fernet keys via SHA256(master_key) without a salt.
    """
    legacy_digest = hashlib.sha256(master_key.encode("utf-8")).digest()
    legacy_key = base64.urlsafe_b64encode(legacy_digest)
    return Fernet(legacy_key)

def derive_vault_cipher(master_key: str, vault_enc_salt_b64: str, iterations: int) -> Fernet:
    salt = _b64decode(vault_enc_salt_b64)
    derived = _pbkdf2_derive(master_key, salt, iterations, dklen=32)
    fernet_key = base64.urlsafe_b64encode(derived)
    return Fernet(fernet_key)

def fernet_encrypt_json(data: Any, cipher: Fernet) -> str:
    plaintext = json.dumps(data, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return cipher.encrypt(plaintext).decode("ascii")

def fernet_decrypt_json(token: str, cipher: Fernet) -> Any:
    decrypted = cipher.decrypt(token.encode("ascii"))
    return json.loads(decrypted.decode("utf-8"))

def legacy_decrypt_str(enc_text: str, master_key: str) -> str:
    return get_legacy_cipher(master_key).decrypt(enc_text.encode("ascii")).decode("utf-8")

# ---------------- USER STORAGE ---------------- #
def load_users():
    return _safe_load_json(USERS_FILE, default={})

def save_users(users):
    try:
        _atomic_write_json(USERS_FILE, users)
    except OSError:
        logger.exception("Failed writing users.json")
        s("Could not save user data. Check permissions.")

# ---------------- USER PASSWORD HASHING ---------------- #
def _pbkdf2(password: str, salt: bytes, iterations: int = 200_000) -> bytes:
    # PBKDF2-HMAC-SHA256 is built-in (no extra deps) and slows down brute-force attempts.
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)

def hash_password(password: str):
    salt = os.urandom(16)
    digest = _pbkdf2(password, salt)
    return (
        base64.urlsafe_b64encode(salt).decode("ascii"),
        base64.urlsafe_b64encode(digest).decode("ascii"),
    )

def verify_password(password: str, salt_b64: str, digest_b64: str) -> bool:
    try:
        salt = base64.urlsafe_b64decode(salt_b64.encode("ascii"))
        expected = base64.urlsafe_b64decode(digest_b64.encode("ascii"))
    except Exception:
        return False
    actual = _pbkdf2(password, salt)
    return hmac.compare_digest(actual, expected)

def migrate_legacy_users_to_hashed_passwords():
    """
    If `users.json` contains plaintext `password`, convert it to hashed+salted and delete the plaintext.
    This runs automatically on startup.
    """
    users = load_users()
    changed = False
    for uname, rec in list(users.items()):
        if isinstance(rec, dict) and "password" in rec and "password_hash" not in rec:
            salt_b64, hash_b64 = hash_password(rec["password"])
            rec.pop("password", None)
            rec["password_salt"] = salt_b64
            rec["password_hash"] = hash_b64
            changed = True
        # Recovery codes are intentionally removed; discard any legacy recovery fields.
        if isinstance(rec, dict) and ("recovery_salt" in rec or "recovery_hash" in rec):
            rec.pop("recovery_salt", None)
            rec.pop("recovery_hash", None)
            changed = True
    if changed:
        save_users(users)

# ---------------- AUTH ---------------- #
def signup():
    users = load_users()
    username = input("Choose username: ")

    if username in users:
        s("Username already exists!")
        return None

    password = getpass.getpass("Choose password: ")
    salt_b64, hash_b64 = hash_password(password)

    users[username] = {
        "password_salt": salt_b64,
        "password_hash": hash_b64,
        "login_fail_count": 0,
        "lockout_until": 0,
    }

    save_users(users)
    s("Signup successful!")
    return username

def login():
    users = load_users()
    username = input("Username: ")
    password = getpass.getpass("Password: ")

    if username not in users:
        s("Invalid credentials!")
        return None

    rec = users[username]
    # Apply lockout even if this is a legacy user record.
    now = int(time.time())
    lockout_until = int(rec.get("lockout_until", 0) or 0)
    if lockout_until and now < lockout_until:
        remaining = lockout_until - now
        s(f"Too many attempts. Try again in {remaining} seconds.")
        logger.warning("Login locked out for username=%s remaining=%ss", username, remaining)
        return None

    if "password_hash" in rec and "password_salt" in rec:
        lockout_until = int(rec.get("lockout_until", 0) or 0)
        fail_count = int(rec.get("login_fail_count", 0) or 0)

        if lockout_until and now < lockout_until:
            remaining = lockout_until - now
            s(f"Too many attempts. Try again in {remaining} seconds.")
            logger.warning("Login locked out for username=%s remaining=%ss", username, remaining)
            return None

        if verify_password(password, rec["password_salt"], rec["password_hash"]):
            rec["login_fail_count"] = 0
            rec["lockout_until"] = 0
            save_users(users)
            s("Login successful!")
            logger.info("Login success username=%s", username)
            return username

        fail_count += 1
        rec["login_fail_count"] = fail_count

        if fail_count >= MAX_LOGIN_ATTEMPTS:
            rec["lockout_until"] = now + LOCKOUT_SECONDS
            logger.warning("Login locked username=%s after %s failures", username, fail_count)
            save_users(users)
            s(f"Too many attempts. Locked for {LOCKOUT_SECONDS} seconds.")
            return None

        # Small delay discourages fast brute forcing without impacting usability much.
        sleep(min(1.0, 0.2 * fail_count))
        save_users(users)
        logger.info("Login failure username=%s fail_count=%s", username, fail_count)
        s("Invalid credentials!")
        return None

    # Extremely defensive fallback: if migration didn't run for some reason.
    if "password" in rec and rec["password"] == password:
        rec["login_fail_count"] = 0
        rec["lockout_until"] = 0
        save_users(users)
        s("Login successful!")
        logger.info("Login success (legacy record) username=%s", username)
        return username

    # Legacy wrong password: also enforce lockout/attempt limits.
    fail_count = int(rec.get("login_fail_count", 0) or 0) + 1
    rec["login_fail_count"] = fail_count
    if fail_count >= MAX_LOGIN_ATTEMPTS:
        rec["lockout_until"] = now + LOCKOUT_SECONDS
        save_users(users)
        logger.warning("Login locked (legacy record) username=%s after %s failures", username, fail_count)
        s(f"Too many attempts. Locked for {LOCKOUT_SECONDS} seconds.")
        return None

    sleep(min(1.0, 0.2 * fail_count))
    save_users(users)
    logger.info("Login failure (legacy record) username=%s fail_count=%s", username, fail_count)
    s("Invalid credentials!")
    return None

# ---------------- PASSWORD STORAGE ---------------- #
def get_file(username):
    return os.path.join(BASE_DIR, PASSWORD_VAULT_FILE_FMT.format(username=username))

def get_master_key_legacy_path(username: str) -> str:
    return os.path.join(BASE_DIR, MASTER_KEY_LEGACY_TXT_FMT.format(username=username))

def get_master_key_meta_path(username: str) -> str:
    return os.path.join(BASE_DIR, MASTER_KEY_META_JSON_FMT.format(username=username))

def _ensure_master_key_metadata(username: str) -> bool:
    """
    Ensures we never keep the master key in plaintext at rest.

    If a legacy plaintext file exists, we migrate it immediately into a salted PBKDF2 hash +
    a separate vault-encryption salt, and then securely erase the plaintext file.
    """
    meta_path = get_master_key_meta_path(username)
    if os.path.exists(meta_path):
        return True

    legacy_path = get_master_key_legacy_path(username)
    if os.path.exists(legacy_path):
        try:
            with open(legacy_path, "r", encoding="utf-8") as f:
                legacy_master_key = f.read()
        except OSError:
            logger.exception("Failed reading legacy master key file")
            s("Could not read legacy master key data.")
            return False

        # Create new metadata from the legacy master key.
        master_salt = os.urandom(MASTER_KEY_SALT_LEN)
        master_hash = _pbkdf2_derive(legacy_master_key, master_salt, MASTER_KEY_PBKDF2_ITERATIONS, dklen=32)
        vault_enc_salt = os.urandom(VAULT_ENC_SALT_LEN)

        meta = {
            "version": MASTER_KEY_META_VERSION,
            "master_salt": _b64encode(master_salt),
            "master_hash": _b64encode(master_hash),
            "master_iterations": MASTER_KEY_PBKDF2_ITERATIONS,
            "vault_enc_salt": _b64encode(vault_enc_salt),
            "vault_enc_iterations": VAULT_ENC_PBKDF2_ITERATIONS,
        }
        try:
            _atomic_write_json(meta_path, meta)
        except OSError:
            logger.exception("Failed writing master key metadata")
            s("Could not create master key metadata.")
            return False

        # Best-effort secure erase (overwrite then delete).
        try:
            try:
                size = os.path.getsize(legacy_path)
                with open(legacy_path, "wb") as f:
                    f.write(os.urandom(size))
                    f.flush()
                    os.fsync(f.fileno())
            except OSError:
                pass
            os.remove(legacy_path)
        except OSError:
            # If deletion fails, we still refuse to proceed, since plaintext would remain on disk.
            logger.exception("Failed erasing legacy master key plaintext file")
            s("Security error: could not erase legacy master key plaintext file.")
            return False

        return True

    # New user: set master key for first time.
    k1 = getpass.getpass("Set Master Key: ")
    k2 = getpass.getpass("Confirm Master Key: ")
    if k1 != k2:
        s("Master keys do not match.")
        return False
    if not k1:
        s("Master key cannot be empty.")
        return False

    master_salt = os.urandom(MASTER_KEY_SALT_LEN)
    master_hash = _pbkdf2_derive(k1, master_salt, MASTER_KEY_PBKDF2_ITERATIONS, dklen=32)
    vault_enc_salt = os.urandom(VAULT_ENC_SALT_LEN)

    meta = {
        "version": MASTER_KEY_META_VERSION,
        "master_salt": _b64encode(master_salt),
        "master_hash": _b64encode(master_hash),
        "master_iterations": MASTER_KEY_PBKDF2_ITERATIONS,
        "vault_enc_salt": _b64encode(vault_enc_salt),
        "vault_enc_iterations": VAULT_ENC_PBKDF2_ITERATIONS,
    }
    try:
        _atomic_write_json(meta_path, meta)
    except OSError:
        logger.exception("Failed writing master key metadata")
        s("Could not create master key metadata.")
        return False

    return True

# ---------------- MASTER KEY ---------------- #
def _load_master_key_meta(username: str) -> Optional[Dict[str, Any]]:
    return _safe_load_json(get_master_key_meta_path(username), default=None)

def _verify_master_key(master_key: str, meta: Dict[str, Any]) -> bool:
    try:
        salt = _b64decode(meta["master_salt"])
        stored_hash = _b64decode(meta["master_hash"])
        iterations = int(meta.get("master_iterations", MASTER_KEY_PBKDF2_ITERATIONS))
    except Exception:
        return False
    actual_hash = _pbkdf2_derive(master_key, salt, iterations, dklen=32)
    return hmac.compare_digest(actual_hash, stored_hash)

def get_master_key(username: str) -> Optional[str]:
    if not _ensure_master_key_metadata(username):
        return None

    meta = _load_master_key_meta(username)
    if not isinstance(meta, dict):
        s("Master key metadata missing or corrupted.")
        return None

    key = getpass.getpass("Enter Master Key: ")
    if _verify_master_key(key, meta):
        return key

    s("Wrong Master Key!")
    logger.info("Master key verification failed username=%s", username)
    return None

def _load_vault(username: str, cipher: Fernet, master_key: str) -> Tuple[Dict[str, Any], bool]:
    """
    Returns (store_dict, migrated).
    If the vault file is in legacy format, it will be decrypted and migrated by the caller.
    """
    vault_path = get_file(username)
    if not os.path.exists(vault_path):
        return {}, False

    raw = _safe_load_json(vault_path, default=None)
    if not isinstance(raw, dict):
        return {}, False

    # New vault format
    if raw.get("version") == VAULT_VERSION and "ciphertext" in raw:
        try:
            decrypted = fernet_decrypt_json(raw["ciphertext"], cipher)
            if isinstance(decrypted, dict):
                return decrypted, False
        except (InvalidToken, ValueError, json.JSONDecodeError, UnicodeDecodeError, TypeError):
            logger.warning("Vault decryption failed username=%s (InvalidToken/JSON)", username)
            s("Could not decrypt your password vault. Check your Master Key.")
            return {}, False

        s("Vault file format is invalid.")
        return {}, False

    # Legacy vault format: { title: {user: ..., password: <encrypted string>} }
    legacy_cipher = get_legacy_cipher(master_key)
    migrated: Dict[str, Any] = {}
    for title, rec in raw.items():
        if not isinstance(rec, dict):
            continue
        enc_pwd = rec.get("password")
        if not isinstance(enc_pwd, str):
            continue
        try:
            dec_pwd = legacy_cipher.decrypt(enc_pwd.encode("ascii")).decode("utf-8")
        except Exception:
            s("Could not decrypt legacy vault. Check your Master Key.")
            logger.warning("Legacy vault decryption failed username=%s", username)
            return {}, False

        migrated[title] = {
            "user": rec.get("user", ""),
            "password": dec_pwd,
        }

    return migrated, True

def _save_vault(username: str, store: Dict[str, Any], cipher: Fernet) -> None:
    vault_path = get_file(username)
    payload = {
        "version": VAULT_VERSION,
        "ciphertext": fernet_encrypt_json(store, cipher),
    }
    try:
        _atomic_write_json(vault_path, payload)
    except OSError:
        logger.exception("Failed writing vault for username=%s", username)
        s("Could not save your password vault. Check permissions.")

# ---------------- PASSWORD OPS ---------------- #
def generate_password(length: int = 16) -> str:
    lower = string.ascii_lowercase
    upper = string.ascii_uppercase
    digits = string.digits
    symbols = "!@#$%^&*()-_=+[]{};:,.?/"

    if length < 4:
        alphabet = lower + upper + digits + symbols
        return "".join(secrets.choice(alphabet) for _ in range(length))

    # Ensure basic variety.
    password_chars = [
        secrets.choice(lower),
        secrets.choice(upper),
        secrets.choice(digits),
        secrets.choice(symbols),
    ]
    alphabet = lower + upper + digits + symbols
    password_chars.extend(secrets.choice(alphabet) for _ in range(length - 4))
    secrets.SystemRandom().shuffle(password_chars)
    return "".join(password_chars)

def open_vault_session(username: str) -> Optional[Tuple[Dict[str, Any], Fernet]]:
    master_key = get_master_key(username)
    if not master_key:
        return None

    meta = _load_master_key_meta(username)
    if not isinstance(meta, dict):
        s("Master key metadata missing or corrupted.")
        return None

    try:
        vault_enc_salt_b64 = meta["vault_enc_salt"]
        iterations = int(meta.get("vault_enc_iterations", VAULT_ENC_PBKDF2_ITERATIONS))
        cipher = derive_vault_cipher(master_key, vault_enc_salt_b64, iterations)
    except Exception:
        logger.exception("Failed deriving vault cipher")
        s("Could not derive encryption key. Check master key metadata.")
        return None

    store, migrated = _load_vault(username, cipher, master_key)
    if migrated:
        _save_vault(username, store, cipher)
    return store, cipher

def add_password(username):
    sess = open_vault_session(username)
    if not sess:
        return
    data, cipher = sess
    title = input("Title: ")
    user = input("Email/Username: ")

    choice = input("Generate random password? (y/N): ").strip().lower()
    if choice == "y":
        length_in = input("Length (default 16): ").strip()
        try:
            length = int(length_in) if length_in else 16
        except ValueError:
            length = 16
        pwd = generate_password(max(8, min(64, length)))
        print("Generated password:", pwd)
    else:
        pwd = getpass.getpass("Password: ")

    if not title:
        s("Title cannot be empty.")
        return

    data[title] = {"user": user, "password": pwd}
    _save_vault(username, data, cipher)

    s("Saved successfully!")

def view_passwords(username):
    sess = open_vault_session(username)
    if not sess:
        return
    data, _cipher = sess
    if not data:
        s("No passwords found!")
        return

    for t in data:
        s(f"\n[Vault] {t}")
        s(f"User: {data[t].get('user','')}")
        s(f"Password: {data[t].get('password','')}")

def delete_password(username):
    sess = open_vault_session(username)
    if not sess:
        return
    data, cipher = sess
    title = input("Enter title to delete: ")

    if title in data:
        del data[title]
        _save_vault(username, data, cipher)
        s("Deleted!")
    else:
        s("Not found!")

# ---------------- FORGOT PASSWORD ---------------- #
def forgot_password():
    users = load_users()
    username = input("Username: ")

    if username not in users:
        s("User not found!")
        return

    # Practical + secure option: reset requires the user's Master Key file.
    # This avoids any additional secrets like recovery codes or email OTPs.
    master_key = get_master_key(username)
    if not master_key:
        return

    rec = users[username]
    new_pass = getpass.getpass("New password: ")
    salt_b64, hash_b64 = hash_password(new_pass)
    rec["password_salt"] = salt_b64
    rec["password_hash"] = hash_b64
    rec["login_fail_count"] = 0
    rec["lockout_until"] = 0
    rec.pop("password", None)  # legacy plaintext field if present
    save_users(users)
    s("Password updated!")
    logger.info("Forgot-password reset username=%s", username)

# ---------------- MENU ---------------- #
def menu(username):
    if not _ensure_master_key_metadata(username):
        return

    while True:
        s("\n1. Add Password")
        s("2. View Passwords")
        s("3. Delete Password")
        s("4. Logout")

        ch = input("Choice: ")

        if ch == "1":
            add_password(username)
        elif ch == "2":
            view_passwords(username)
        elif ch == "3":
            delete_password(username)
        elif ch == "4":
            break

# ---------------- MAIN ---------------- #
def main():
    # Ensure passwords are encrypted (hashed) before any login/reset logic.
    migrate_legacy_users_to_hashed_passwords()
    while True:
        s("\n1. Signup")
        s("2. Login")
        s("3. Forgot Password")
        s("4. Exit")

        ch = input("Select: ")

        if ch == "1":
            u = signup()
            if u:
                menu(u)
        elif ch == "2":
            u = login()
            if u:
                menu(u)
        elif ch == "3":
            forgot_password()
        elif ch == "4":
            break

if __name__ == "__main__":
    main()