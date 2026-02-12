import bcrypt
from fastapi import HTTPException, status
from typing import List
from ..repositories.user_repo import UserRepository
from ..utils.blob_storage import generate_sas_url


class UserService:
    def __init__(self):
        self.repo = UserRepository()

    def _attach_sas(self, user: dict) -> dict:
        if user and user.get("profilepictureurl"):
            user["profilepictureurl"] = generate_sas_url(user["profilepictureurl"])
        return user

    def create_user(self, user_data) -> dict:
        hashed_pw = bcrypt.hashpw(
            user_data.password.encode(), bcrypt.gensalt()
        ).decode()

        db_data = {
            "UserID": user_data.userid,
            "Name": user_data.name,
            "Email": user_data.email,
            "Password": hashed_pw,
            "RoleID": user_data.roleid,
        }

        try:
            new_user = self.repo.create(db_data)
            return self._attach_sas(new_user)
        except ValueError as e:

            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Gagal membuat pengguna. Kemungkinan Email '{user_data.email}' atau ID sudah terdaftar.",
            )

    def get_all_users(
        self,
        include_inactive: bool,
        role_ids: List[int] = None,
        q: str = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list:
        return self.repo.get_all(include_inactive, role_ids, q, limit, offset)

    def get_user_by_id(self, user_id: int) -> dict:
        user = self.repo.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Pengguna dengan ID {user_id} tidak ditemukan.",
            )
        return user

    def update_self_name(self, user_id: int, name: str) -> dict:
        self.repo.update_profile_name(user_id, name)
        updated_user = self.repo.get_by_id(user_id)
        return self._attach_sas(updated_user)

    def change_own_password(self, user_id: int, current_pw: str, new_pw: str):
        stored_pw = self.repo.verify_password(user_id)

        if not stored_pw or not bcrypt.checkpw(current_pw.encode(), stored_pw.encode()):

            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Password saat ini tidak sesuai. Silakan coba lagi.",
            )

        new_hashed = bcrypt.hashpw(new_pw.encode(), bcrypt.gensalt()).decode()
        self.repo.update_password(user_id, new_hashed)
        return {"message": "Password Anda berhasil diperbarui."}

    def admin_update_user(self, user_id: int, update_data) -> dict:
        schema_map = {
            "name": "Name",
            "email": "Email",
            "roleid": "RoleID",
            "isactive": "IsActive",
        }

        raw_dict = update_data.model_dump(exclude_unset=True)
        if not raw_dict:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tidak ada perubahan data yang dikirim. Mohon periksa kembali input Anda.",
            )

        db_values = {schema_map[k]: v for k, v in raw_dict.items() if k in schema_map}

        existing_user = self.repo.get_by_id(user_id)
        if not existing_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Pengguna dengan ID {user_id} tidak ditemukan.",
            )

        try:
            success = self.repo.update_sensitive_data(user_id, db_values)
            if not success:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Gagal memperbarui data. Pengguna mungkin sudah dihapus.",
                )
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email tersebut sudah digunakan oleh pengguna lain.",
            )

        updated_user = self.repo.get_by_id(user_id)
        return self._attach_sas(updated_user)

    def admin_force_reset_password(self, user_id: int, new_password: str):

        target_user = self.repo.get_by_id(user_id)

        if not target_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Pengguna dengan ID {user_id} tidak ditemukan.",
            )

        new_hashed = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
        self.repo.update_password(user_id, new_hashed)

        user_name = target_user.get("name") or target_user.get("Name")
        return {"message": f"Password untuk pengguna '{user_name}' berhasil direset."}

    def toggle_active_status(
        self, user_id: int, is_active: bool, current_admin_id: int
    ):
        if not is_active and user_id == current_admin_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Anda tidak dapat menonaktifkan akun sendiri saat sedang login.",
            )

        target_user = self.repo.get_by_id(user_id)

        if not target_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Pengguna dengan ID {user_id} tidak ditemukan.",
            )

        success = self.repo.set_active_status(user_id, is_active)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Gagal memperbarui status pengguna.",
            )

        status_text = "diaktifkan" if is_active else "dinonaktifkan"
        user_name = target_user.get("name") or target_user.get("Name") or "Tanpa Nama"

        return {
            "message": f"Akun pengguna '{user_name}' berhasil {status_text}.",
            "user_id": user_id,
            "new_status": "Active" if is_active else "Inactive",
        }
