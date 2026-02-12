import os
import jwt
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException, Security, Depends, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from ..utils.blob_storage import generate_sas_url
from ..repositories.user_repo import UserRepository

JWT_SECRET = os.getenv("JWT_SECRET")
JWT_ALGORITHM = "HS256"

security = HTTPBearer()


def create_access_token(data: dict):
    to_encode = data.copy()
    # expire = datetime.now(timezone.utc) + timedelta(hours=1)
    expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)


def create_refresh_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=7)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_jwt(token: str):
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


def get_current_user(auth: HTTPAuthorizationCredentials = Security(security)) -> dict:
    token = auth.credentials
    payload = decode_jwt(token)
    user_email = payload.get("sub")

    if user_email is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload"
        )

    repo = UserRepository()
    user = repo.get_by_email(user_email)

    if user is None or not user["isactive"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or not active",
        )

    if user.get("refreshtoken") is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sesi telah berakhir (Logout Detected). Silakan login kembali.",
        )

    user["profilepictureurl_path"] = user.get("profilepictureurl")
    if user.get("profilepictureurl"):
        user["profilepictureurl"] = generate_sas_url(user["profilepictureurl"])

    return user


def get_current_admin_user(current_user: dict = Security(get_current_user)) -> dict:
    if current_user.get("roleid") != 1:
        raise HTTPException(
            status_code=403, detail="Akses ditolak. Hanya admin yang diizinkan."
        )
    return current_user