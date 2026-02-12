from datetime import datetime
from typing import Optional, List
from psycopg2 import errors
from ..utils.db import db_connect, fetch_one_as_dict, fetch_all_as_dict


class UserRepository:
    def get_all(
        self,
        include_inactive: bool = False,
        role_ids: List[int] = None,
        q: str = None,
        limit: int = 20,
        offset: int = 0,
    ) -> List[dict]:
        query = """
            SELECT 
                u.UserID, u.Name, u.Email, u.RoleID, r.RoleName, 
                u.IsActive
            FROM sipa.Users u
            LEFT JOIN sipa.Roles r ON u.RoleID = r.RoleID
            WHERE 1=1
        """
        params = []

        if not include_inactive:
            query += " AND u.IsActive = TRUE"

        if role_ids:
            query += " AND u.RoleID = ANY(%s)"
            params.append(role_ids)

        if q:
            search_param = f"%{q}%"
            query += " AND (u.Name ILIKE %s OR CAST(u.UserID AS TEXT) ILIKE %s)"
            params.extend([search_param, search_param])

        query += " ORDER BY u.UserID ASC"
        query += " LIMIT %s OFFSET %s"
        params.extend([limit, offset])

        return fetch_all_as_dict(query, tuple(params))

    def get_by_id(self, user_id: int) -> Optional[dict]:
        query = """
            SELECT u.*, r.RoleName 
            FROM sipa.Users u
            LEFT JOIN sipa.Roles r ON u.RoleID = r.RoleID
            WHERE u.UserID = %s
        """
        return fetch_one_as_dict(query, (user_id,))

    def verify_password(self, user_id: int) -> Optional[str]:
        query = "SELECT Password FROM sipa.Users WHERE UserID = %s"
        res = fetch_one_as_dict(query, (user_id,))
        return res["password"] if res else None

    def get_by_email(self, email: str) -> Optional[dict]:
        query = "SELECT * FROM sipa.Users WHERE Email = %s"
        return fetch_one_as_dict(query, (email,))

    def create(self, user_data: dict) -> dict:
        conn = db_connect()
        try:
            with conn.cursor() as cursor:
                query = """
                    INSERT INTO sipa.Users (UserID, Name, Email, Password, RoleID)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING UserID, Name, Email, RoleID, ProfilePictureURL, IsActive
                """
                cursor.execute(
                    query,
                    (
                        user_data["UserID"],
                        user_data["Name"],
                        user_data["Email"],
                        user_data["Password"],
                        user_data["RoleID"],
                    ),
                )
                new_user_row = cursor.fetchone()
                columns = [desc[0].lower() for desc in cursor.description]
                res = dict(zip(columns, new_user_row))
                conn.commit()
                return res
        except errors.UniqueViolation as e:
            conn.rollback()
            raise ValueError("ID Karyawan atau Email sudah terdaftar.")
        finally:
            conn.close()

    def update_password(self, user_id: int, hashed_password: str):
        conn = db_connect()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE sipa.Users SET Password = %s, PasswordResetToken = NULL, 
                    PasswordResetTokenExpiresAt = NULL, FailedLoginAttempts = 0, 
                    IsLocked = FALSE, UpdatedAt = CURRENT_TIMESTAMP WHERE UserID = %s
                    """,
                    (hashed_password, user_id),
                )
                conn.commit()
        finally:
            conn.close()

    def update_sensitive_data(self, user_id: int, update_values: dict) -> bool:
        if not update_values:
            return False
        set_clauses = [f"{k} = %s" for k in update_values.keys()]
        set_clauses.append("UpdatedAt = CURRENT_TIMESTAMP")
        params = list(update_values.values()) + [user_id]
        query = f"UPDATE sipa.Users SET {', '.join(set_clauses)} WHERE UserID = %s"

        conn = db_connect()
        try:
            with conn.cursor() as cursor:
                cursor.execute(query, tuple(params))
                conn.commit()
                return cursor.rowcount > 0
        finally:
            conn.close()

    def update_profile_name(self, user_id: int, name: str) -> bool:
        conn = db_connect()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "UPDATE sipa.Users SET Name = %s, UpdatedAt = CURRENT_TIMESTAMP WHERE UserID = %s",
                    (name, user_id),
                )
                conn.commit()
                return True
        finally:
            conn.close()

    def set_active_status(self, user_id: int, is_active: bool) -> bool:
        conn = db_connect()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "UPDATE sipa.Users SET IsActive = %s WHERE UserID = %s",
                    (is_active, user_id),
                )
                conn.commit()
                return cursor.rowcount > 0
        finally:
            conn.close()

    def update_profile_picture(self, user_id: int, blob_path: str) -> None:
        conn = db_connect()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "UPDATE sipa.Users SET ProfilePictureURL = %s, UpdatedAt = CURRENT_TIMESTAMP WHERE UserID = %s",
                    (blob_path, user_id),
                )
                conn.commit()
        finally:
            conn.close()
