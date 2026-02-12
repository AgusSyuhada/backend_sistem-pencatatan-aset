from fastapi import APIRouter, Depends, Security, Query
from typing import List, Optional
from ..utils.security import get_current_user, get_current_admin_user
from ..services.lookup_service import LookupService
from ..schemas.lookup_schema import (
    RoleResponse,
    TeamResponse,
    TeamCreate,
    ManufacturerResponse,
    ManufacturerCreate,
    ConditionResponse,
    ConditionCreate,
    LocationResponse,
    LocationCreate,
    CostCenterResponse,
    CostCenterCreate,
)

router = APIRouter(prefix="/lookups", tags=["Master Lookups"])


def get_service():
    return LookupService()


@router.get("/roles", response_model=List[RoleResponse])
def get_roles(
    service: LookupService = Depends(get_service),
    user: dict = Security(get_current_user),
):
    return service.get_roles()


@router.get("/teams", response_model=List[TeamResponse])
def get_teams(
    q: Optional[str] = None,
    service: LookupService = Depends(get_service),
    user: dict = Security(get_current_user),
):
    return service.get_teams(q)


@router.post("/teams", response_model=TeamResponse, status_code=201)
def create_team(
    payload: TeamCreate,
    service: LookupService = Depends(get_service),
    admin: dict = Security(get_current_admin_user),
):
    return service.create_team(payload.teamname)


@router.get("/manufacturers", response_model=List[ManufacturerResponse])
def get_manufacturers(
    q: Optional[str] = None,
    service: LookupService = Depends(get_service),
    user: dict = Security(get_current_user),
):
    return service.get_manufacturers(q)


@router.post("/manufacturers", response_model=ManufacturerResponse, status_code=201)
def create_manufacturer(
    payload: ManufacturerCreate,
    service: LookupService = Depends(get_service),
    admin: dict = Security(get_current_admin_user),
):
    return service.create_manufacturer(payload.manufacturername)


@router.get("/conditions", response_model=List[ConditionResponse])
def get_conditions(
    q: Optional[str] = None,
    service: LookupService = Depends(get_service),
    user: dict = Security(get_current_user),
):
    return service.get_conditions(q)


@router.get("/costcenters", response_model=List[CostCenterResponse])
def get_cost_centers(
    q: Optional[str] = None,
    service: LookupService = Depends(get_service),
    user: dict = Security(get_current_user),
):
    return service.get_cost_centers(q)


@router.post("/costcenters", response_model=CostCenterResponse, status_code=201)
def create_cost_center(
    payload: CostCenterCreate,
    service: LookupService = Depends(get_service),
    admin: dict = Security(get_current_admin_user),
):
    return service.create_cost_center(payload.costcentercode)


@router.get("/locations", response_model=List[LocationResponse])
def get_locations(
    area: Optional[str] = Query(None, description="Cari berdasarkan nama Area"),
    location: Optional[str] = Query(None, description="Cari berdasarkan nama Lokasi"),
    service: LookupService = Depends(get_service),
    user: dict = Security(get_current_user),
):

    return service.get_locations(area_q=area, location_q=location)


@router.post("/locations", response_model=LocationResponse, status_code=201)
def create_location(
    payload: LocationCreate,
    service: LookupService = Depends(get_service),
    user: dict = Security(get_current_user),
):
    return service.create_location(
        payload.saplocationcode,
        payload.area,
        payload.location,
    )