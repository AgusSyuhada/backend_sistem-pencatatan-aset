from fastapi import (
    APIRouter,
    Security,
    Depends,
    status,
    Query,
    File,
    UploadFile,
    HTTPException,
)
from typing import Optional, List

from ..schemas.user_schema import (
    UserDataResponse,
    UserDetailResponse,
    UserSelfUpdate,
    ChangePasswordRequest,
    UserCreate,
    UserAdminUpdate,
    AdminResetPassword,
    UserListResponse,
)
from ..schemas.common_schema import MessageResponse
from ..utils.security import get_current_user, get_current_admin_user
from ..services.user_service import UserService
from ..services.upload_service import UploadService
from ..repositories.user_repo import UserRepository

router = APIRouter(prefix="/users", tags=["Users Management"])


def get_service():
    return UserService()


def get_upload_service():
    return UploadService()


def get_repo():
    return UserRepository()


@router.post(
    "/me/profile-picture",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
)
async def upload_my_profile_picture(
    file: UploadFile = File(...),
    upload_service: UploadService = Depends(get_upload_service),
    user_repo: UserRepository = Depends(get_repo),
    current_user: dict = Security(get_current_user),
):
    user_id = current_user["userid"]
    old_path = current_user.get("profilepictureurl_path")

    new_blob_path = upload_service.upload_profile_picture(file, user_id)

    try:
        user_repo.update_profile_picture(user_id, new_blob_path)
    except Exception as e:
        upload_service.delete_old_file(new_blob_path)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Gagal memperbarui database: {str(e)}",
        )

    if old_path and old_path != new_blob_path:
        upload_service.delete_old_file(old_path)

    return {"message": "Foto profil Anda berhasil diperbarui."}


@router.post("/", response_model=UserDataResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    user_data: UserCreate,
    service: UserService = Depends(get_service),
    current_admin: dict = Security(get_current_admin_user),
):
    new_user = service.create_user(user_data)
    user_name = new_user.get("name") or new_user.get("Name")
    return {
        "message": f"Pengguna baru '{user_name}' berhasil ditambahkan.",
        "user": new_user,
    }


@router.get("/", response_model=UserListResponse)
def get_all_users(
    q: Optional[str] = None,
    include_inactive: bool = False,
    role_ids: Optional[List[int]] = Query(None),
    limit: int = 20,
    offset: int = 0,
    service: UserService = Depends(get_service),
    current_admin: dict = Security(get_current_admin_user),
):
    users = service.get_all_users(include_inactive, role_ids, q, limit, offset)
    return {"message": "Daftar pengguna berhasil diambil.", "data": users}


@router.get("/me", response_model=UserDataResponse)
def get_my_profile(
    service: UserService = Depends(get_service),
    current_user: dict = Security(get_current_user),
):
    user = service.repo.get_by_id(current_user["userid"])
    return {
        "message": "Data pengguna berhasil diambil.",
        "user": service._attach_sas(user),
    }


@router.get("/{user_id}", response_model=UserDetailResponse)
def get_user_detail(
    user_id: int,
    service: UserService = Depends(get_service),
    current_admin: dict = Security(get_current_admin_user),
):
    user = service.get_user_by_id(user_id)
    user_name = user.get("name") or user.get("Name")

    return {
        "message": f"Data pengguna '{user_name}' berhasil diambil.",
        "user": user,
    }


@router.patch("/me", response_model=UserDataResponse)
def update_my_name(
    update_data: UserSelfUpdate,
    service: UserService = Depends(get_service),
    current_user: dict = Security(get_current_user),
):
    updated_user = service.update_self_name(current_user["userid"], update_data.name)
    name_display = updated_user.get("name") or updated_user.get("Name")
    return {
        "message": f"Nama profil berhasil diubah menjadi '{name_display}'.",
        "user": updated_user,
    }


@router.put("/me/password", response_model=MessageResponse)
def change_my_password(
    password_data: ChangePasswordRequest,
    service: UserService = Depends(get_service),
    current_user: dict = Security(get_current_user),
):
    return service.change_own_password(
        current_user["userid"],
        password_data.current_password,
        password_data.new_password,
    )


@router.patch(
    "/{user_id}", response_model=UserDataResponse, status_code=status.HTTP_200_OK
)
def update_user_sensitive_data(
    user_id: int,
    update_data: UserAdminUpdate,
    service: UserService = Depends(get_service),
    current_admin: dict = Security(get_current_admin_user),
):
    updated_user = service.admin_update_user(user_id, update_data)
    user_name = updated_user.get("name") or updated_user.get("Name")

    return {
        "message": f"Data pengguna '{user_name}' berhasil diperbarui.",
        "user": updated_user,
    }


@router.put("/{user_id}/reset-password", response_model=MessageResponse)
def admin_reset_password(
    user_id: int,
    reset_data: AdminResetPassword,
    service: UserService = Depends(get_service),
    current_admin: dict = Security(get_current_admin_user),
):
    return service.admin_force_reset_password(user_id, reset_data.new_password)


@router.post("/{user_id}/deactivate", response_model=MessageResponse)
def deactivate_user(
    user_id: int,
    service: UserService = Depends(get_service),
    current_admin: dict = Security(get_current_admin_user),
):
    return service.toggle_active_status(user_id, False, current_admin["userid"])


@router.post("/{user_id}/reactivate", response_model=MessageResponse)
def reactivate_user(
    user_id: int,
    service: UserService = Depends(get_service),
    current_admin: dict = Security(get_current_admin_user),
):
    return service.toggle_active_status(user_id, True, current_admin["userid"])
