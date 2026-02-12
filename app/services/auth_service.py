import bcrypt
import pytz
import logging
from datetime import timedelta
from fastapi import HTTPException, BackgroundTasks, status
from ..repositories.auth_repo import AuthRepository
from ..schemas.auth_schema import LoginRequest, TokenResponse, MessageResponse
from ..utils.security import create_access_token, create_refresh_token, decode_jwt
from ..utils.email import send_email_acs
from ..utils.geo import get_city_from_coordinates
from ..utils.common import (
    get_current_time_wib,
    format_display_time,
    generate_numeric_otp,
)
from ..utils.email_templates import (
    get_otp_template,
    get_login_alert_template,
    get_password_reset_success_template,
)

logger = logging.getLogger(__name__)


class AuthService:
    def __init__(self):
        self.repo = AuthRepository()

    def authenticate_user(
        self,
        login_data: LoginRequest,
        request_info: dict,
        background_tasks: BackgroundTasks,
    ) -> dict:
        user = self.repo.get_by_email(login_data.email)
        now_wib = get_current_time_wib()

        invalid_credentials_msg = "Email atau password yang Anda masukkan salah."

        if not user:
            raise HTTPException(
                status.HTTP_401_UNAUTHORIZED, detail=invalid_credentials_msg
            )

        if not user["isactive"]:
            raise HTTPException(
                status.HTTP_401_UNAUTHORIZED, detail=invalid_credentials_msg
            )

        if user["islocked"]:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                detail="Akun dikunci sementara karena terlalu banyak percobaan login gagal.",
            )

        if not bcrypt.checkpw(login_data.password.encode(), user["password"].encode()):
            self._handle_failed_login(user, now_wib)
            raise HTTPException(
                status.HTTP_401_UNAUTHORIZED, detail=invalid_credentials_msg
            )

        self._check_device_conflict(user, login_data.device_model, now_wib)

        access_token = create_access_token(
            data={"sub": user["email"], "role": user["roleid"]}
        )
        refresh_token = create_refresh_token(data={"sub": user["email"]})
        refresh_token_expiry = now_wib + timedelta(days=7)

        city_name = get_city_from_coordinates(login_data.geo_coordinates)
        time_str = format_display_time(now_wib)

        self.repo.update_login_success(
            user_id=user["userid"],
            refresh_token=refresh_token,
            refresh_expires_at=refresh_token_expiry,
            ip=request_info["ip"],
            agent=request_info["agent"],
            coordinates=login_data.geo_coordinates,
            city=city_name,
            device_model=login_data.device_model,
            login_time_wib=now_wib,
        )

        template = get_login_alert_template(
            user["name"], time_str, login_data.device_model, city_name
        )
        background_tasks.add_task(
            send_email_acs,
            to_email=user["email"],
            subject=template["subject"],
            html_content=template["html_content"],
            plain_content=template["plain_content"],
        )

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "message": "Login berhasil.",
            "token_type": "bearer",
        }

    def request_forgot_password(self, email: str, background_tasks: BackgroundTasks):
        user = self.repo.get_by_email(email)

        default_message = (
            "Jika email terdaftar, kode OTP akan dikirimkan ke email Anda."
        )

        if not user or not user["isactive"]:
            return {"message": default_message}

        now_wib = get_current_time_wib()

        if user["passwordresettokenexpiresat"]:
            token_expires = user["passwordresettokenexpiresat"]
            if token_expires.tzinfo is None:
                token_expires = pytz.utc.localize(token_expires).astimezone(
                    now_wib.tzinfo
                )

            remaining_time = token_expires - now_wib

            if remaining_time.total_seconds() > 240:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Mohon tunggu 1 menit sebelum meminta kode OTP baru.",
                )

        otp = generate_numeric_otp()
        expires_at = now_wib + timedelta(minutes=5)

        self.repo.save_reset_token(user["userid"], otp, expires_at)

        template = get_otp_template(user["name"], otp)
        background_tasks.add_task(
            send_email_acs,
            to_email=email,
            subject=template["subject"],
            html_content=template["html_content"],
            plain_content=template["plain_content"],
        )

        return {"message": default_message}

    def verify_otp(self, email: str, otp: str):
        user = self.repo.get_by_email(email)
        now_wib = get_current_time_wib()

        is_valid = False
        if user and user["passwordresettoken"] == otp:
            token_expires = user["passwordresettokenexpiresat"]
            if token_expires:
                if token_expires.tzinfo is None:
                    token_expires = pytz.utc.localize(token_expires).astimezone(
                        now_wib.tzinfo
                    )

                if now_wib <= token_expires:
                    is_valid = True

        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Kode OTP salah atau sudah kedaluwarsa.",
            )

        return {"message": "Kode OTP valid.", "valid": True}

    def reset_password(
        self, email: str, otp: str, new_password: str, background_tasks: BackgroundTasks
    ):

        self.verify_otp(email, otp)

        user = self.repo.get_by_email(email)
        now_wib = get_current_time_wib()

        hashed_password = bcrypt.hashpw(
            new_password.encode(), bcrypt.gensalt()
        ).decode()
        self.repo.reset_password(user["userid"], hashed_password)

        time_str = format_display_time(now_wib)
        template = get_password_reset_success_template(user["name"], time_str)

        background_tasks.add_task(
            send_email_acs,
            to_email=email,
            subject=template["subject"],
            html_content=template["html_content"],
            plain_content=template["plain_content"],
        )

        return {
            "message": "Password berhasil diubah. Silakan login dengan password baru."
        }

    def refresh_access_token(self, token: str):
        try:
            payload = decode_jwt(token)
            if payload.get("type") != "refresh":
                raise HTTPException(
                    status.HTTP_401_UNAUTHORIZED,
                    detail="Token tidak valid (bukan refresh token).",
                )

            user = self.repo.get_by_email(payload.get("sub"))
            if not user:
                raise HTTPException(
                    status.HTTP_401_UNAUTHORIZED,
                    detail="User credential tidak ditemukan.",
                )

            if user["refreshtoken"] != token:
                raise HTTPException(
                    status.HTTP_401_UNAUTHORIZED,
                    detail="Refresh token tidak valid atau telah digunakan.",
                )

            now_wib = get_current_time_wib()
            token_expires = user["refreshtokenexpiresat"]

            if not token_expires:
                raise HTTPException(
                    status.HTTP_401_UNAUTHORIZED, detail="Sesi invalid."
                )

            if token_expires.tzinfo is None:
                token_expires = pytz.utc.localize(token_expires).astimezone(
                    now_wib.tzinfo
                )

            if now_wib > token_expires:
                raise HTTPException(
                    status.HTTP_401_UNAUTHORIZED,
                    detail="Sesi telah berakhir. Silakan login ulang.",
                )

            new_access_token = create_access_token(
                {"sub": user["email"], "role": user["roleid"]}
            )
            new_refresh_token = create_refresh_token({"sub": user["email"]})
            new_expires_at = now_wib + timedelta(days=7)

            self.repo.update_refresh_token(
                user["userid"], new_refresh_token, new_expires_at
            )

            return {
                "access_token": new_access_token,
                "refresh_token": new_refresh_token,
                "message": "Sesi berhasil diperbarui.",
                "token_type": "bearer",
            }
        except HTTPException as he:
            raise he
        except Exception:
            raise HTTPException(
                status.HTTP_401_UNAUTHORIZED,
                detail="Token tidak valid atau kedaluwarsa.",
            )

    def logout_user(self, user_id: int, device_model: str):
        success = self.repo.logout(user_id, device_model)
        if not success:
            logger.warning(
                f"User {user_id} mencoba logout dari {device_model} tapi sesi tidak ditemukan."
            )
        return {"message": "Logout berhasil."}

    def _handle_failed_login(self, user, now_wib):
        new_attempts = user["failedloginattempts"] + 1
        is_locked = new_attempts >= 5

        self.repo.update_login_failure(user["userid"], new_attempts, now_wib, is_locked)

        if is_locked:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Akun Anda kini dikunci karena 5x gagal login.",
            )

    def _check_device_conflict(self, user, current_device_model, now_wib):
        active_model = user.get("lastlogindevicemodel")

        if user.get("devicelastusedat"):
            last_used = user["devicelastusedat"]
            if last_used.tzinfo is None:
                last_used = pytz.utc.localize(last_used).astimezone(now_wib.tzinfo)

            diff = now_wib - last_used

            is_device_expired = diff.total_seconds() > 86400
        else:
            is_device_expired = True

        if (
            active_model
            and active_model != current_device_model
            and not is_device_expired
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Akun sedang aktif di perangkat {active_model}. Silakan logout terlebih dahulu.",
            )
