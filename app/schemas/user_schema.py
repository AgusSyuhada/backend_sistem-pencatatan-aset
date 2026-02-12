from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field


class UserProfile(BaseModel):
    userid: int
    name: str
    email: EmailStr
    roleid: int
    profilepictureurl: Optional[str] = None


class UserListInfo(BaseModel):
    userid: int
    name: str
    email: EmailStr
    roleid: int
    rolename: Optional[str] = None
    isactive: bool
    lastlogin: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserCreate(BaseModel):
    userid: int = Field(..., description="ID Karyawan")
    name: str = Field(..., min_length=3)
    email: EmailStr
    password: str = Field(..., min_length=6)
    roleid: int = Field(..., description="1=Admin, 2=User")


class UserSelfUpdate(BaseModel):
    name: str = Field(..., min_length=3, max_length=100)


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=6)


class UserAdminUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=3)
    email: Optional[EmailStr] = None
    roleid: Optional[int] = None
    isactive: Optional[bool] = None


class AdminResetPassword(BaseModel):
    new_password: str = Field(..., min_length=6)


class UserDataResponse(BaseModel):
    message: str
    user: UserProfile


class UserDetailResponse(BaseModel):
    message: str
    user: UserListInfo


class UserListResponse(BaseModel):
    message: str
    data: List[UserListInfo]
