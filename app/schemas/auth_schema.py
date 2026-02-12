from typing import Optional
from pydantic import BaseModel, EmailStr, Field
from .common_schema import MessageResponse


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    device_model: str
    geo_coordinates: str
    location_name: Optional[str] = None


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    message: str
    notification_status: Optional[str] = None


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    device_model: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class VerifyOtpRequest(BaseModel):
    email: EmailStr
    otp: str = Field(..., min_length=6, max_length=6)


class ResetPasswordRequest(BaseModel):
    email: EmailStr
    otp: str = Field(..., min_length=6, max_length=6)
    new_password: str = Field(..., min_length=6)
