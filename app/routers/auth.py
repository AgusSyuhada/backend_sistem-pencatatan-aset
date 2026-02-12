from fastapi import (
    APIRouter,
    Request,
    Header,
    Security,
    Depends,
    BackgroundTasks,
    status,
)
from ..schemas.auth_schema import (
    LoginRequest,
    TokenResponse,
    RefreshTokenRequest,
    LogoutRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    VerifyOtpRequest,
)
from ..schemas.common_schema import MessageResponse
from ..services.auth_service import AuthService
from ..utils.security import get_current_user

router = APIRouter()


def get_auth_service():
    return AuthService()


@router.post("/login", response_model=TokenResponse, status_code=status.HTTP_200_OK)
def login(
    login_data: LoginRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    service: AuthService = Depends(get_auth_service),
    x_login_type: str = Header(alias="X-Login-Type", default=None),
    x_device_info: str = Header(alias="X-Device-Info", default=None),
):
    request_info = {
        "ip": request.client.host,
        "agent": request.headers.get("User-Agent", "Unknown"),
    }
    return service.authenticate_user(login_data, request_info, background_tasks)


@router.post("/logout", response_model=MessageResponse, status_code=status.HTTP_200_OK)
def logout(
    logout_data: LogoutRequest,
    current_user: dict = Security(get_current_user),
    service: AuthService = Depends(get_auth_service),
):
    return service.logout_user(current_user["userid"], logout_data.device_model)


@router.post("/refresh", response_model=TokenResponse, status_code=status.HTTP_200_OK)
def refresh(
    refresh_data: RefreshTokenRequest, service: AuthService = Depends(get_auth_service)
):
    return service.refresh_access_token(refresh_data.refresh_token)


@router.post(
    "/forgot-password",
    response_model=MessageResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def forgot_password(
    request_data: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    service: AuthService = Depends(get_auth_service),
):
    return service.request_forgot_password(request_data.email, background_tasks)


@router.post("/verify-otp", status_code=status.HTTP_200_OK)
def verify_otp_endpoint(
    request_data: VerifyOtpRequest,
    service: AuthService = Depends(get_auth_service),
):
    return service.verify_otp(request_data.email, request_data.otp)


@router.post(
    "/reset-password", response_model=MessageResponse, status_code=status.HTTP_200_OK
)
def reset_password(
    request_data: ResetPasswordRequest,
    background_tasks: BackgroundTasks,
    service: AuthService = Depends(get_auth_service),
):
    return service.reset_password(
        request_data.email,
        request_data.otp,
        request_data.new_password,
        background_tasks,
    )
