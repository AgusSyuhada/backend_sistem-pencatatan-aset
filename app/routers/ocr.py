from fastapi import APIRouter, Security, HTTPException, File, UploadFile, Depends
from ..utils.security import get_current_user
from ..schemas.ocr_schema import OcrResponse
from ..schemas.asset_schema import CycleStatusInfo, CyclePeriodInfo
from ..services.ocr_service import OcrService
from ..repositories.asset_repo import AssetRepository
from ..repositories.cycle_repo import CycleRepository

router = APIRouter(prefix="/ocr", tags=["OCR"])


def get_ocr_service():
    return OcrService()


def get_asset_repo():
    return AssetRepository()


def get_cycle_repo():
    return CycleRepository()


@router.post("/scan-asset-code", response_model=OcrResponse)
async def scan_asset_code(
    file: UploadFile = File(..., description="File gambar scan."),
    service: OcrService = Depends(get_ocr_service),
    asset_repo: AssetRepository = Depends(get_asset_repo),
    cycle_repo: CycleRepository = Depends(get_cycle_repo),
    current_user: dict = Security(get_current_user),
):
    image_bytes = await file.read()
    if not image_bytes:
        raise HTTPException(
            status_code=400, detail="File gambar tidak ditemukan atau kosong."
        )

    extracted_code, raw_text = service.process_image(image_bytes)

    if isinstance(raw_text, str):
        raw_text = [raw_text]

    if not extracted_code:
        return OcrResponse(
            message="Kode aset tidak ditemukan dalam gambar.",
            found=False,
            raw_text=raw_text,
        )

    asset = asset_repo.get_by_asset_number(extracted_code)

    if not asset:
        return OcrResponse(
            message=f"Kode {extracted_code} terbaca, namun aset tidak terdaftar di sistem.",
            found=False,
            asset_number=extracted_code,
            raw_text=raw_text,
        )

    latest_period = cycle_repo.get_latest_period()
    is_in_cycle = False
    cycle_period_info = None

    if latest_period:
        is_in_cycle = cycle_repo.is_asset_in_cycle(
            asset["assetnumber"], latest_period["year"], latest_period["cycle"]
        )
        cycle_period_info = CyclePeriodInfo(
            year=latest_period["year"], cycle=latest_period["cycle"]
        )

    is_admin = current_user.get("roleid") == 1
    can_edit = False
    warning_message = None

    if is_in_cycle:
        can_edit = True
    else:
        if is_admin:
            can_edit = True
            warning_message = "Aset ini berada di Luar siklus aktif. Perubahan akan langsung berdampak pada Master Data."
        else:
            can_edit = False
            warning_message = "Aset ini tidak terdaftar dalam jadwal saat ini. Anda hanya dapat melihat detail aset."

    main_message = f"Aset ditemukan dengan nomor aset {asset['assetnumber']}."

    status_obj = CycleStatusInfo(
        is_in_cycle=is_in_cycle,
        cycle_period=cycle_period_info,
        can_edit=can_edit,
        warning_message=warning_message,
    )

    return OcrResponse(
        message=main_message,
        found=True,
        asset_number=asset["assetnumber"],
        asset_name=asset.get("assetname"),
        raw_text=raw_text,
        status=status_obj,
    )
