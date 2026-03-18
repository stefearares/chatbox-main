from datetime import datetime, timedelta, timezone
from jose import jwt
from config.settings import settings

# TIP: load_env should always run before trying to access the env vars so it gets injected and the os can retrieve it
# if settings.settings.env_mode != "production":
#    load_dotenv()


if not settings.jwt_secret_key:
    raise RuntimeError("JWT_SECRET_KEY missing, check env vars.")

ALGORITHM = "HS256"
EXPIRE_MINUTES = 60 * 24


def create_access_token(user_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=EXPIRE_MINUTES)
    payload = {"sub": str(user_id), "exp": int(expire.timestamp())}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            return None
        return payload
    except (jwt.JWTError, ValueError):
        return None
