from fastapi import (
    APIRouter,
    Security,
    HTTPException,
    BackgroundTasks,
    Depends,
    Query,
    Form,
    File,
    UploadFile,
    status,
)
from fastapi.responses import Response
from typing import List, Optional
from datetime import datetime
from app.services.report_service import ReportService
from ..schemas.asset_schema import (
    CreatePeriodRequest,
    UpdatePeriodRequest,
    AssetCycleListResponse,
    PeriodStatsResponse,
    CycleStatusInfo,
    CyclePeriodInfo,
    SingleAssetCycleResponse,
)
from ..schemas.common_schema import MessageResponse
from ..utils.security import get_current_user, get_current_admin_user
from ..repositories.cycle_repo import CycleRepository
from ..repositories.asset_repo import AssetRepository
from ..services.storage_service import StorageService
from ..services.sync_service import GSheetSyncService
from ..services.upload_service import UploadService

router = APIRouter(prefix="/assets", tags=["Assets Cycle Management"])


def get_cycle_repo():
    return CycleRepository()


def get_asset_repo():
    return AssetRepository()


def get_sync_service():
    return GSheetSyncService()


def get_upload_service():
    return UploadService()


def ensure_period_exists(year: int, cycle: int, repo: CycleRepository):
    if not repo.check_exists(year, cycle):
        raise HTTPException(
            status_code=404,
            detail=f"Periode Siklus {cycle} Tahun {year} tidak ditemukan.",
        )


def _format_date_val(value):
    if isinstance(value, datetime):
        return value.strftime("%d-%b-%Y")
    elif value:
        try:
            val_str = str(value)[:10]
            dt = datetime.strptime(val_str, "%Y-%m-%d")
            return dt.strftime("%d-%b-%Y")
        except (ValueError, TypeError):
            return str(value)
    return value


def _process_asset_dates(asset: dict):
    if not asset:
        return asset
    date_fields = ["inventorydate", "InventoryDate"]
    for field in date_fields:
        if field in asset and asset[field]:
            asset[field] = _format_date_val(asset[field])
    return asset


def calculate_current_period():
    now = datetime.now()
    year = now.year
    month = now.month

    if 1 <= month <= 4:
        cycle = 1
    elif 5 <= month <= 8:
        cycle = 2
    else:
        cycle = 3

    return year, cycle


@router.get("/periods", response_model=AssetCycleListResponse)
def get_asset_periods(
    q: Optional[str] = Query(None, description="Cari Tahun atau Siklus"),
    limit: int = 20,
    offset: int = 0,
    repo: CycleRepository = Depends(get_cycle_repo),
    current_user: dict = Security(get_current_user),
):
    data = repo.get_periods(q, limit, offset)
    return {"message": "Success", "data": data}


@router.post("/periods", response_model=MessageResponse)
def create_new_period(
    period_data: CreatePeriodRequest,
    background_tasks: BackgroundTasks,
    repo: CycleRepository = Depends(get_cycle_repo),
    sync_service: GSheetSyncService = Depends(get_sync_service),
    current_admin: dict = Security(get_current_admin_user),
):
    if period_data.cycle < 1 or period_data.cycle > 3:
        raise HTTPException(
            status_code=400,
            detail="Siklus tidak valid. Hanya diperbolehkan Siklus periode Jan-Apr, Mei-Ags dan Sep-Des.",
        )

    if repo.check_exists(period_data.year, period_data.cycle):
        raise HTTPException(
            status_code=409,
            detail=f"Siklus {period_data.cycle} Tahun {period_data.year} sudah ada.",
        )

    asset_numbers = list(set(period_data.asset_numbers))
    if not asset_numbers:
        raise HTTPException(status_code=400, detail="Daftar aset kosong.")

    repo.copy_master_to_cycle(asset_numbers, period_data.year, period_data.cycle)
    background_tasks.add_task(
        sync_service.sync_cycle_data, period_data.year, period_data.cycle
    )

    return {
        "message": f"Siklus {period_data.cycle}/{period_data.year} berhasil dibuat."
    }


@router.patch("/periods/{year}/{cycle}", response_model=MessageResponse)
def update_period_assets(
    year: int,
    cycle: int,
    period_data: UpdatePeriodRequest,
    background_tasks: BackgroundTasks,
    repo: CycleRepository = Depends(get_cycle_repo),
    sync_service: GSheetSyncService = Depends(get_sync_service),
    current_admin: dict = Security(get_current_admin_user),
):
    ensure_period_exists(year, cycle, repo)

    current_assets_dicts = repo.get_by_period(year, cycle)
    current_assets_set = {a["assetnumber"] for a in current_assets_dicts}
    requested_assets_set = set(period_data.asset_numbers)

    to_add = list(requested_assets_set - current_assets_set)
    to_remove = list(current_assets_set - requested_assets_set)

    if to_remove:
        repo.delete_assets_from_cycle(year, cycle, to_remove)
    if to_add:
        repo.copy_master_to_cycle(to_add, year, cycle)

    background_tasks.add_task(sync_service.sync_cycle_data, year, cycle)
    return {
        "message": f"Update berhasil: {len(to_add)} ditambah, {len(to_remove)} dihapus."
    }


@router.delete("/periods/{year}/{cycle}", response_model=MessageResponse)
def delete_period(
    year: int,
    cycle: int,
    background_tasks: BackgroundTasks,
    repo: CycleRepository = Depends(get_cycle_repo),
    sync_service: GSheetSyncService = Depends(get_sync_service),
    current_admin: dict = Security(get_current_admin_user),
):
    ensure_period_exists(year, cycle, repo)
    repo.delete_period(year, cycle)
    background_tasks.add_task(sync_service.delete_cycle_sheet, year, cycle)
    return {"message": "Periode siklus berhasil dihapus."}


@router.get("/periods/{year}/{cycle}/stats", response_model=PeriodStatsResponse)
def get_period_stats(
    year: int,
    cycle: int,
    repo: CycleRepository = Depends(get_cycle_repo),
    current_user: dict = Security(get_current_user),
):
    ensure_period_exists(year, cycle, repo)
    stats = repo.get_statistics(year, cycle)
    if not stats:
        return {
            "message": "Data siklus kosong atau tidak ditemukan.",
            "year": year,
            "cycle": cycle,
            "summary": {
                "total_assets": 0,
                "cycled_assets": 0,
                "pending_assets": 0,
                "completion_percentage": 0,
                "total_asset_value": 0,
            },
            "distributions": {
                "condition": [],
                "team": [],
                "area": [],
                "inventory_result": [],
                "manufacturer": [],
                "cost_center": [],
            },
            "timeline": [],
        }
    return stats


@router.get("/cycle/data")
def get_assets_by_cycle(
    cycle: int,
    year: int,
    q: Optional[str] = None,
    location_ids: Optional[List[int]] = Query(None),
    condition_ids: Optional[List[int]] = Query(None),
    limit: int = 20,
    offset: int = 0,
    repo: CycleRepository = Depends(get_cycle_repo),
    current_user: dict = Security(get_current_user),
):
    ensure_period_exists(year, cycle, repo)
    assets = repo.get_by_period(
        year,
        cycle,
        q,
        location_ids=location_ids,
        condition_ids=condition_ids,
        limit=limit,
        offset=offset,
    )

    for asset in assets:
        _process_asset_dates(asset)
    return {"message": "Success", "data": assets}


@router.get(
    "/cycle/{year}/{cycle}/{asset_number}", response_model=SingleAssetCycleResponse
)
def get_cycle_asset_detail(
    year: int,
    cycle: int,
    asset_number: str,
    repo: CycleRepository = Depends(get_cycle_repo),
    current_user: dict = Security(get_current_user),
):
    ensure_period_exists(year, cycle, repo)

    asset = repo.get_single_cycle_asset(year, cycle, asset_number)
    if not asset:
        raise HTTPException(
            status_code=404, detail="Aset tidak ditemukan di siklus ini."
        )

    asset = StorageService.attach_sas_urls(asset)

    real_year, real_cycle = calculate_current_period()
    is_active_period = year == real_year and cycle == real_cycle

    is_future_period = (year > real_year) or (year == real_year and cycle > real_cycle)

    warning_message = None
    if is_future_period:
        warning_message = f"Periode siklus {cycle}/{year} belum dimulai (Saat ini: {real_cycle}/{real_year})."
    elif not is_active_period:
        warning_message = f"Periode siklus {cycle}/{year} telah berakhir (Saat ini: {real_cycle}/{real_year}). Data bersifat Read-Only."

    status_info = CycleStatusInfo(
        is_in_cycle=True,
        cycle_period=CyclePeriodInfo(year=year, cycle=cycle),
        can_edit=is_active_period,
        warning_message=warning_message,
    )

    return {
        "message": "Found",
        "data": asset,
        "status": status_info,
    }


@router.patch("/cycle/{year}/{cycle}/{asset_number}")
def update_cycle_asset(
    year: int,
    cycle: int,
    asset_number: str,
    gpscoordinate: Optional[str] = Form(None),
    conditionid: Optional[int] = Form(None),
    locationid: Optional[int] = Form(None),
    specificlocation: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    inventoryresult: Optional[str] = Form(None),
    picteamfav: Optional[str] = Form(None),
    inventorydate: Optional[str] = Form(None),
    asset_photo: Optional[UploadFile] = File(None),
    code_photo: Optional[UploadFile] = File(None),
    location_photo: Optional[UploadFile] = File(None),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    cycle_repo: CycleRepository = Depends(get_cycle_repo),
    asset_repo: AssetRepository = Depends(get_asset_repo),
    upload_service: UploadService = Depends(get_upload_service),
    sync_service: GSheetSyncService = Depends(get_sync_service),
    current_user: dict = Security(get_current_user),
):
    ensure_period_exists(year, cycle, cycle_repo)

    real_year, real_cycle = calculate_current_period()
    if not (year == real_year and cycle == real_cycle):
        raise HTTPException(
            status_code=403,
            detail=f"Periode {cycle}/{year} tidak aktif (sudah berakhir atau belum dimulai).",
        )

    current_cycle_asset = cycle_repo.get_single_cycle_asset(year, cycle, asset_number)
    if not current_cycle_asset:
        raise HTTPException(
            status_code=404, detail="Aset tidak ditemukan di siklus ini."
        )

    backup_id = current_cycle_asset["backupid"]

    pic_ids = None
    if picteamfav is not None:
        try:
            pic_ids = [
                int(n.strip()) for n in picteamfav.split(",") if n.strip().isdigit()
            ]
        except ValueError:
            pic_ids = []

    update_data = {}
    if gpscoordinate is not None:
        update_data["GPSCoordinate"] = gpscoordinate
    if conditionid is not None:
        update_data["ConditionID"] = conditionid
    if locationid is not None:
        update_data["LocationID"] = locationid
    if specificlocation is not None:
        update_data["SpecificLocation"] = specificlocation
    if description is not None:
        update_data["Description"] = description
    if inventoryresult is not None:
        update_data["InventoryResult"] = inventoryresult
    if inventorydate is not None:
        update_data["InventoryDate"] = inventorydate

    upload_files = [
        ("Asset", asset_photo),
        ("Code", code_photo),
        ("Location", location_photo),
    ]

    for p_type, p_file in upload_files:
        if p_file:
            blob_path = upload_service.upload_asset_photo(
                p_file, asset_number, year, cycle, p_type
            )
            cycle_repo.add_asset_photo(
                asset_number, year, cycle, backup_id, p_type, blob_path
            )

    cycle_repo.update_cycle_asset(backup_id, update_data, pic_ids)

    master_update_map = {
        "GPSCoordinate": "gpscoordinate",
        "ConditionID": "conditionid",
        "LocationID": "locationid",
        "SpecificLocation": "specificlocation",
        "Description": "description",
        "InventoryResult": "inventoryresult",
        "InventoryDate": "inventorydate",
    }
    master_data_payload = {}
    for db_key, val in update_data.items():
        if db_key in master_update_map:
            master_data_payload[master_update_map[db_key]] = val

    if master_data_payload or pic_ids is not None:
        asset_repo.update(asset_number, master_data_payload, pic_ids)

    background_tasks.add_task(sync_service.sync_cycle_data, year, cycle)
    background_tasks.add_task(sync_service.sync_master_data)

    updated_asset = cycle_repo.get_single_cycle_asset(year, cycle, asset_number)

    status_info = CycleStatusInfo(
        is_in_cycle=True,
        cycle_period=CyclePeriodInfo(year=year, cycle=cycle),
        can_edit=True,
        warning_message=None,
    )

    return {
        "message": "Updated",
        "data": StorageService.attach_sas_urls(updated_asset),
        "status": status_info,
    }


@router.delete("/cycle/{year}/{cycle}/{asset_number}", response_model=MessageResponse)
def remove_asset_from_cycle(
    year: int,
    cycle: int,
    asset_number: str,
    background_tasks: BackgroundTasks,
    repo: CycleRepository = Depends(get_cycle_repo),
    sync_service: GSheetSyncService = Depends(get_sync_service),
    current_admin: dict = Security(get_current_admin_user),
):
    ensure_period_exists(year, cycle, repo)

    deleted = repo.delete_assets_from_cycle(year, cycle, [asset_number])
    if not deleted:
        raise HTTPException(
            status_code=404, detail="Aset tidak ditemukan di siklus tersebut."
        )

    background_tasks.add_task(sync_service.sync_cycle_data, year, cycle)
    return {"message": "Aset berhasil dihapus dari siklus."}


@router.get("/periods/{year}/{cycle}/report/excel")
def download_cycle_report_excel(
    year: int,
    cycle: int,
    repo: CycleRepository = Depends(get_cycle_repo),
    current_admin: dict = Security(get_current_admin_user),
):
    ensure_period_exists(year, cycle, repo)
    stats = repo.get_statistics(year, cycle)
    assets_raw = repo.get_all_assets_by_period(year, cycle)

    formatted_assets = []
    for idx, a in enumerate(assets_raw):
        formatted_assets.append(
            {
                "index": idx + 1,
                "asset_number": a.get("assetnumber") or "-",
                "hbm": a.get("hbm") or "-",
                "asset_name": a.get("assetname") or "-",
                "team": a.get("teamname") or "-",
                "val": "{:,.0f}".format(a.get("assetvalue") or 0).replace(",", "."),
                "cc": a.get("costcenter") or "-",
                "serial": a.get("serialnumber") or "-",
                "model": a.get("modeltype") or "-",
                "brand": a.get("manufacturername") or "-",
                "gps": a.get("gpscoordinate") or "-",
                "cond": a.get("conditionname") or "-",
                "sap": a.get("saplocationcode") or "-",
                "area": a.get("area") or "-",
                "loc": a.get("location") or "-",
                "spec": a.get("specificlocation") or "-",
                "desc": a.get("description") or "-",
                "res": a.get("inventoryresult") or "-",
                "date": _format_date_val(a.get("inventorydate")),
                "pic": a.get("picteamfav") or "-",
            }
        )

    report_data = {
        "year": year,
        "cycle": cycle,
        "total_assets": stats["summary"]["total_assets"],
        "cycled_assets": stats["summary"]["cycled_assets"],
        "pending_assets": stats["summary"]["pending_assets"],
        "total_asset_value": "{:,.0f}".format(
            stats["summary"]["total_asset_value"]
        ).replace(",", "."),
        "dist_condition": stats["distributions"]["condition"],
        "dist_area": stats["distributions"]["area"],
        "assets": formatted_assets,
    }

    excel_bytes = ReportService.generate_cycle_excel(report_data)

    filename = f"Laporan_Siklus_{cycle}_{year}.xlsx"

    return Response(
        content=excel_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )