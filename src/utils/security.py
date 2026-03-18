from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, InvalidHash


hasher = PasswordHasher(
    time_cost=3,
    memory_cost=65000,
    parallelism=4,
    hash_len=32,
    salt_len=16,
)


def hash_password(norm_password: str) -> str:
    return hasher.hash(norm_password)


def verify_password(hashed_password: str, norm_password: str) -> bool:
    try:
        return hasher.verify(hashed_password, norm_password)
    except (VerifyMismatchError, InvalidHash):
        return False
