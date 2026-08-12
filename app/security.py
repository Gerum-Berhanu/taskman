from pwdlib import PasswordHash


password_hash = PasswordHash.recommended()


def get_password_hash(password: str) -> str:
    return password_hash.hash(password)


def get_dummy_hash(dummy_password: str) -> str:
    return password_hash.hash(dummy_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return password_hash.verify(plain_password, hashed_password)

