from datetime import datetime
from typing import Optional
from ..utils.db import db_connect, fetch_one_as_dict


class AuthRepository:
    def get_by_email(self, email: str):
        query = "SELECT * FROM sipa.Users WHERE Email = %s"
        return fetch_one_as_dict(query, (email,))

    def verify_password(self, user_id: int) -> Optional[str]:
        res = fetch_one_as_dict(
            "SELECT Password FROM sipa.Users WHERE UserID = %s", (user_id,)
        )
        return res["password"] if res else None

    def update_login_failure(
        self, user_id: int, new_attempts: int, updated_at: datetime, lock: bool = False
    ):
        conn = db_connect()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "UPDATE sipa.Users SET FailedLoginAttempts = %s WHERE UserID = %s",
                    (new_attempts, user_id),
                )
                if lock:
                    cursor.execute(
                        "UPDATE sipa.Users SET IsLocked = TRUE WHERE UserID = %s",
                        (user_id,),
                    )
                conn.commit()
        finally:
            conn.close()

    def update_login_success(
        self,
        user_id: int,
        refresh_token: str,
        refresh_expires_at: datetime,
        ip: str,
        agent: str,
        coordinates: str,
        city: str,
        device_model: str,
        login_time_wib: datetime,
    ):
        conn = db_connect()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE sipa.Users 
                    SET 
                        LastLogin = %s, 
                        LastLoginIP = %s,
                        LastLoginAgent = %s,
                        LastLoginCoordinates = %s,
                        LastLoginCity = %s,         
                        LastLoginDeviceModel = %s,
                        DeviceLastUsedAt = %s,
                        LastLogout = NULL,
                        FailedLoginAttempts = 0,
                        IsLocked = FALSE,
                        RefreshToken = %s,
                        RefreshTokenExpiresAt = %s
                    WHERE UserID = %s
                    """,
                    (
                        login_time_wib,
                        ip,
                        agent,
                        coordinates,
                        city,
                        device_model,
                        login_time_wib,
                        refresh_token,
                        refresh_expires_at,
                        user_id,
                    ),
                )
                conn.commit()
        finally:
            conn.close()

    def reset_password(self, user_id: int, hashed_password: str):
        conn = db_connect()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE sipa.Users
                    SET Password = %s,
                        PasswordResetToken = NULL,
                        PasswordResetTokenExpiresAt = NULL,
                        FailedLoginAttempts = 0,
                        IsLocked = FALSE
                    WHERE UserID = %s
                    """,
                    (hashed_password, user_id),
                )
                conn.commit()
        finally:
            conn.close()

    def save_reset_token(self, user_id: int, otp: str, expires_at: datetime):
        conn = db_connect()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "UPDATE sipa.Users SET PasswordResetToken = %s, PasswordResetTokenExpiresAt = %s WHERE UserID = %s",
                    (otp, expires_at, user_id),
                )
                conn.commit()
        finally:
            conn.close()

    def update_refresh_token(
        self, user_id: int, new_refresh_token: str, expires_at: datetime
    ):
        conn = db_connect()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE sipa.Users 
                    SET RefreshToken = %s, RefreshTokenExpiresAt = %s
                    WHERE UserID = %s
                    """,
                    (new_refresh_token, expires_at, user_id),
                )
                conn.commit()
        finally:
            conn.close()

    def logout(self, user_id: int, device_model: str) -> bool:
        conn = db_connect()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE sipa.Users 
                    SET 
                        RefreshToken = NULL, 
                        LastLoginDeviceModel = NULL,      
                        LastLogout = CURRENT_TIMESTAMP
                    WHERE UserID = %s 
                      AND LastLoginDeviceModel = %s       
                    """,
                    (user_id, device_model),
                )
                conn.commit()
                return cursor.rowcount > 0
        finally:
            conn.close()
