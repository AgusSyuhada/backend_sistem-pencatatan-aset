from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class CyclePeriodInfo(BaseModel):
    year: int
    cycle: int


class AssetCycleContext(BaseModel):
    is_in_active_cycle: bool
    active_period: Optional[CyclePeriodInfo] = None
    message: Optional[str] = None


class CycleStatusInfo(BaseModel):
    is_in_cycle: bool
    cycle_period: Optional[CyclePeriodInfo] = None
    can_edit: bool
    warning_message: Optional[str] = None


class CreatePeriodRequest(BaseModel):
    year: int = Field(..., description="Tahun siklus, cth: 2025")
    cycle: int = Field(..., description="Nomor siklus, cth: 4")
    asset_numbers: List[str] = Field(
        ..., description="Daftar Nomor Aset yang akan disalin ke siklus"
    )


class UpdatePeriodRequest(BaseModel):
    asset_numbers: List[str] = Field(
        ..., description="Daftar LENGKAP nomor aset yang seharusnya ada di siklus ini"
    )


class AssetCycleInfo(BaseModel):
    cycle: int
    year: int
    total_assets: int = 0
    cycled_assets: int = 0
    percentage: float = 0.0


class AssetCycleListResponse(BaseModel):
    message: str
    data: List[AssetCycleInfo]


class AssetCycleData(BaseModel):
    backupid: int
    cycle: int
    year: int
    assetnumber: str
    assetname: str
    hbm: Optional[str] = None
    teamid: Optional[int] = None
    teamname: Optional[str] = None
    assetvalue: Optional[float] = None
    costcenter: Optional[str] = None
    serialnumber: Optional[str] = None
    modeltype: Optional[str] = None
    manufacturerid: Optional[int] = None
    manufacturername: Optional[str] = None
    gpscoordinate: Optional[str] = None
    conditionid: Optional[int] = None
    conditionname: Optional[str] = None
    locationid: Optional[int] = None
    area: Optional[str] = None
    location: Optional[str] = None
    saplocationcode: Optional[str] = None
    specificlocation: Optional[str] = None
    description: Optional[str] = None
    inventoryresult: Optional[str] = None
    inventorydate: Optional[datetime] = None
    picteamfav: Optional[str] = None
    assetcodephoto: Optional[str] = None
    assetphoto: Optional[str] = None
    assetlocationphoto: Optional[str] = None
    createdat: Optional[datetime] = None
    updatedat: Optional[datetime] = None
    backuptimestamp: Optional[datetime] = None
    iscycled: bool = False

    class Config:
        from_attributes = True


class CycleStatusInfo(BaseModel):
    is_in_cycle: bool
    cycle_period: Optional[CyclePeriodInfo] = None
    can_edit: bool
    warning_message: Optional[str] = None


class SingleAssetCycleResponse(BaseModel):
    message: str
    data: AssetCycleData
    status: Optional[CycleStatusInfo] = None


class PeriodStatsResponse(BaseModel):
    message: str
    year: int
    cycle: int
    summary: dict = Field(
        ..., description="Ringkasan total, cycled vs pending, dan nilai aset"
    )
    distributions: dict = Field(
        ..., description="Penyebaran aset berdasarkan berbagai dimensi"
    )
    timeline: List[dict] = Field(
        ..., description="Tren penyelesaian cycle berdasarkan tanggal"
    )
