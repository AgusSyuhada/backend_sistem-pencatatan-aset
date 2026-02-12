from fastapi import (
    APIRouter,
    Form,
    Security,
    HTTPException,
    BackgroundTasks,
    Depends,
    Query,
    UploadFile,
    File,
)
from typing import Optional, List, Any, Dict
from datetime import datetime
from ..schemas.asset_schema import (
    AssetCycleContext,
    CyclePeriodInfo,
)
from ..schemas.common_schema import MessageResponse
from ..utils.security import get_current_user, get_current_admin_user
from ..repositories.asset_repo import AssetRepository
from ..services.storage_service import StorageService
from ..services.sync_service import GSheetSyncService
from ..services.upload_service import UploadService
from ..repositories.cycle_repo import CycleRepository

router = APIRouter(prefix="/assets", tags=["Assets Master"])


def get_repo():
    return AssetRepository()


def get_sync_service():
    return GSheetSyncService()


def get_cycle_repo():
    return CycleRepository()


def get_upload_service():
    return UploadService()


CREATE_MAP = {
    "assetnumber": "AssetNumber",
    "assetname": "AssetName",
    "hbm": "HBM",
    "teamid": "TeamID",
    "assetvalue": "AssetValue",
    "costcenter": "CostCenter",
    "serialnumber": "SerialNumber",
    "modeltype": "ModelType",
    "manufacturerid": "ManufacturerID",
    "gpscoordinate": "GPSCoordinate",
    "conditionid": "ConditionID",
    "locationid": "LocationID",
    "description": "Description",
    "inventoryresult": "InventoryResult",
    "inventorydate": "InventoryDate",
    "specificlocation": "SpecificLocation",
}
UPDATE_MAP = {
    "assetname": "AssetName",
    "hbm": "HBM",
    "teamid": "TeamID",
    "assetvalue": "AssetValue",
    "costcenter": "CostCenter",
    "serialnumber": "SerialNumber",
    "modeltype": "ModelType",
    "manufacturerid": "ManufacturerID",
    "gpscoordinate": "GPSCoordinate",
    "conditionid": "ConditionID",
    "locationid": "LocationID",
    "description": "Description",
    "inventoryresult": "InventoryResult",
    "inventorydate": "InventoryDate",
    "specificlocation": "SpecificLocation",
}


def parse_pic_ids(pic_str: Optional[str]) -> Optional[List[int]]:
    if pic_str is None:
        return None
    try:
        return [int(pid.strip()) for pid in pic_str.split(",") if pid.strip().isdigit()]
    except ValueError:
        return []


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

    target_fields = ["inventorydate", "InventoryDate"]

    for field in target_fields:
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


@router.get("/")
def get_all(
    q: Optional[str] = None,
    include_inactive: bool = False,
    location_ids: Optional[List[int]] = Query(None),
    condition_ids: Optional[List[int]] = Query(None),
    limit: int = 20,
    offset: int = 0,
    repo: AssetRepository = Depends(get_repo),
    current_user: dict = Security(get_current_user),
):
    assets = repo.get_all(
        q=q,
        include_inactive=include_inactive,
        location_ids=location_ids,
        condition_ids=condition_ids,
        limit=limit,
        offset=offset,
    )

    for asset in assets:
        _process_asset_dates(asset)

    assets_sas = StorageService.attach_sas_urls(assets)

    return {"message": "Success", "data": assets_sas}


@router.get("/{asset_number}")
def get_one(
    asset_number: str,
    repo: AssetRepository = Depends(get_repo),
    cycle_repo: CycleRepository = Depends(get_cycle_repo),
    current_user: dict = Security(get_current_user),
):
    asset_dict = repo.get_by_asset_number(asset_number)
    if not asset_dict:
        raise HTTPException(status_code=404, detail="Asset not found")

    asset_dict = _process_asset_dates(asset_dict)
    asset_sas_dict = StorageService.attach_sas_urls(asset_dict)

    current_year, current_cycle = calculate_current_period()

    is_in_active_cycle = False
    active_period_model = None
    cycle_msg = None

    in_active_cycle = cycle_repo.is_asset_in_cycle(
        asset_number, current_year, current_cycle
    )

    if in_active_cycle:
        is_in_active_cycle = True
        active_period_model = CyclePeriodInfo(year=current_year, cycle=current_cycle)
        cycle_msg = None
    else:
        pass

    context_model = AssetCycleContext(
        is_in_active_cycle=is_in_active_cycle,
        active_period=active_period_model,
        message=cycle_msg,
    )

    return {"message": "Found", "data": asset_sas_dict, "cycle_context": context_model}


@router.post("/", status_code=201)
def create(
    assetnumber: str = Form(...),
    assetname: str = Form(...),
    hbm: Optional[str] = Form(None),
    teamid: Optional[int] = Form(None),
    assetvalue: Optional[float] = Form(None),
    costcenter: Optional[str] = Form(None),
    serialnumber: Optional[str] = Form(None),
    modeltype: Optional[str] = Form(None),
    manufacturerid: Optional[int] = Form(None),
    gpscoordinate: Optional[str] = Form(None),
    conditionid: int = Form(...),
    locationid: int = Form(...),
    description: Optional[str] = Form(None),
    inventoryresult: Optional[str] = Form(None),
    inventorydate: Optional[str] = Form(None),
    specificlocation: Optional[str] = Form(None),
    picteamfav: Optional[str] = Form(None),
    asset_photo: Optional[UploadFile] = File(None),
    code_photo: Optional[UploadFile] = File(None),
    location_photo: Optional[UploadFile] = File(None),
    bg_tasks: BackgroundTasks = BackgroundTasks(),
    repo: AssetRepository = Depends(get_repo),
    cycle_repo: CycleRepository = Depends(get_cycle_repo),
    upload_service: UploadService = Depends(get_upload_service),
    sync: GSheetSyncService = Depends(get_sync_service),
    admin: dict = Security(get_current_admin_user),
):
    raw_data = {
        "assetnumber": assetnumber,
        "assetname": assetname,
        "hbm": hbm,
        "teamid": teamid,
        "assetvalue": assetvalue,
        "costcenter": costcenter,
        "serialnumber": serialnumber,
        "modeltype": modeltype,
        "manufacturerid": manufacturerid,
        "gpscoordinate": gpscoordinate,
        "conditionid": conditionid,
        "locationid": locationid,
        "description": description,
        "inventoryresult": inventoryresult,
        "inventorydate": inventorydate,
        "specificlocation": specificlocation,
    }

    pic_ids = parse_pic_ids(picteamfav)
    db_data = {
        CREATE_MAP[k]: v
        for k, v in raw_data.items()
        if k in CREATE_MAP and v is not None
    }

    if repo.get_by_asset_number(assetnumber):
        raise HTTPException(status_code=409, detail="Asset number already exists")

    try:
        new_id = repo.create(db_data, admin["userid"], pic_ids)

        master_asset_full = repo.get_by_asset_number(new_id)

        backup_id = cycle_repo.create_zero_cycle_entry(master_asset_full, pic_ids)

        target_year = 0
        target_cycle = 0

        upload_files = [
            ("Asset", asset_photo),
            ("Code", code_photo),
            ("Location", location_photo),
        ]

        for p_type, p_file in upload_files:
            if p_file:
                blob_path = upload_service.upload_asset_photo(
                    p_file, new_id, target_year, target_cycle, p_type
                )
                cycle_repo.add_asset_photo(
                    new_id, target_year, target_cycle, backup_id, p_type, blob_path
                )

        bg_tasks.add_task(sync.sync_master_data)

        new_asset = repo.get_by_asset_number(new_id)

        _process_asset_dates(new_asset)

        return {"message": "Created and Initialized", "data": new_asset}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Process failed: {str(e)}")


@router.patch("/{asset_number}")
def update(
    asset_number: str,
    assetname: Optional[str] = Form(None),
    hbm: Optional[str] = Form(None),
    teamid: Optional[int] = Form(None),
    assetvalue: Optional[float] = Form(None),
    costcenter: Optional[str] = Form(None),
    serialnumber: Optional[str] = Form(None),
    modeltype: Optional[str] = Form(None),
    manufacturerid: Optional[int] = Form(None),
    gpscoordinate: Optional[str] = Form(None),
    conditionid: Optional[int] = Form(None),
    locationid: Optional[int] = Form(None),
    description: Optional[str] = Form(None),
    inventoryresult: Optional[str] = Form(None),
    inventorydate: Optional[str] = Form(None),
    specificlocation: Optional[str] = Form(None),
    picteamfav: Optional[str] = Form(None),
    asset_photo: Optional[UploadFile] = File(None),
    code_photo: Optional[UploadFile] = File(None),
    location_photo: Optional[UploadFile] = File(None),
    bg_tasks: BackgroundTasks = BackgroundTasks(),
    repo: AssetRepository = Depends(get_repo),
    cycle_repo: CycleRepository = Depends(get_cycle_repo),
    upload_service: UploadService = Depends(get_upload_service),
    sync: GSheetSyncService = Depends(get_sync_service),
    current_user: dict = Security(get_current_user),
):
    user_role = current_user.get("role", "")
    user_role_id = current_user.get("roleid")

    is_admin = False
    if isinstance(user_role, str) and user_role.lower() == "admin":
        is_admin = True
    elif user_role_id == 1:
        is_admin = True

    if not is_admin:

        curr_year, curr_cycle = calculate_current_period()
        in_active_cycle = cycle_repo.is_asset_in_cycle(
            asset_number, curr_year, curr_cycle
        )

        if not in_active_cycle:
            raise HTTPException(
                status_code=403,
                detail=f"User hanya diizinkan mengupdate aset master jika aset tersebut berada dalam Periode Siklus Aktif ({curr_cycle}/{curr_year}).",
            )

        assetname = None
        hbm = None
        teamid = None
        assetvalue = None
        costcenter = None
        serialnumber = None
        modeltype = None
        manufacturerid = None
        inventorydate = None

    raw_data = {
        "assetname": assetname,
        "hbm": hbm,
        "teamid": teamid,
        "assetvalue": assetvalue,
        "costcenter": costcenter,
        "serialnumber": serialnumber,
        "modeltype": modeltype,
        "manufacturerid": manufacturerid,
        "gpscoordinate": gpscoordinate,
        "conditionid": conditionid,
        "locationid": locationid,
        "description": description,
        "inventoryresult": inventoryresult,
        "inventorydate": inventorydate,
        "specificlocation": specificlocation,
    }

    raw_data = {k: v for k, v in raw_data.items() if v is not None}

    pic_ids = parse_pic_ids(picteamfav) if picteamfav is not None else None
    db_data = {UPDATE_MAP[k]: v for k, v in raw_data.items() if k in UPDATE_MAP}

    success = repo.update(asset_number, db_data, pic_ids)
    if not success:
        raise HTTPException(status_code=404, detail="Asset not found")

    curr_year, curr_cycle = calculate_current_period()
    in_active_cycle = cycle_repo.is_asset_in_cycle(asset_number, curr_year, curr_cycle)

    if in_active_cycle:
        cycle_repo.update_from_master_sync(
            asset_number,
            curr_year,
            curr_cycle,
            db_data,
            pic_ids,
        )
        bg_tasks.add_task(sync.sync_cycle_data, curr_year, curr_cycle)

    zero_backup_id = cycle_repo.get_backup_id(asset_number, 0, 0)

    if not zero_backup_id:
        master_asset_full = repo.get_by_asset_number(asset_number)
        current_pics = pic_ids if pic_ids is not None else []
        zero_backup_id = cycle_repo.create_zero_cycle_entry(
            master_asset_full, current_pics
        )
    else:
        cycle_repo.update_cycle_asset(zero_backup_id, db_data, pic_ids)

    upload_files = [
        ("Asset", asset_photo),
        ("Code", code_photo),
        ("Location", location_photo),
    ]

    for p_type, p_file in upload_files:
        if p_file:
            blob_path = upload_service.upload_asset_photo(
                p_file, asset_number, 0, 0, p_type
            )
            cycle_repo.add_asset_photo(
                asset_number, 0, 0, zero_backup_id, p_type, blob_path
            )

    bg_tasks.add_task(sync.sync_master_data)

    return get_one(asset_number, repo, cycle_repo, current_user)


@router.post("/{asset_number}/reactivate", response_model=MessageResponse)
def reactivate(
    asset_number: str,
    bg_tasks: BackgroundTasks,
    repo: AssetRepository = Depends(get_repo),
    sync: GSheetSyncService = Depends(get_sync_service),
    admin: dict = Security(get_current_admin_user),
):
    if not repo.set_active_status(asset_number, True):
        raise HTTPException(status_code=404, detail="Asset not found")

    bg_tasks.add_task(sync.sync_master_data)

    return {"message": f"Asset {asset_number} reactivated"}


@router.post("/{asset_number}/deactivate", response_model=MessageResponse)
def deactivate(
    asset_number: str,
    bg_tasks: BackgroundTasks,
    repo: AssetRepository = Depends(get_repo),
    sync: GSheetSyncService = Depends(get_sync_service),
    admin: dict = Security(get_current_admin_user),
):
    if not repo.set_active_status(asset_number, False):
        raise HTTPException(status_code=404, detail="Asset not found")
    bg_tasks.add_task(sync.sync_master_data)
    return {"message": f"Asset {asset_number} deactivated"}