from typing import List
from pydantic import BaseModel, Field


class RoleResponse(BaseModel):
    roleid: int = Field
    rolename: str = Field


class TeamCreate(BaseModel):
    teamname: str = Field


class TeamResponse(BaseModel):
    teamid: int = Field
    teamname: str = Field


class ManufacturerCreate(BaseModel):
    manufacturername: str = Field


class ManufacturerResponse(BaseModel):
    manufacturerid: int = Field
    manufacturername: str = Field


class ConditionCreate(BaseModel):
    conditionname: str = Field


class ConditionResponse(BaseModel):
    conditionid: int = Field
    conditionname: str = Field


class CostCenterCreate(BaseModel):
    costcentercode: str = Field


class CostCenterResponse(BaseModel):
    costcenterid: int = Field
    costcentercode: str = Field


class LocationCreate(BaseModel):
    saplocationcode: str = Field
    area: str = Field
    location: str = Field


class LocationResponse(BaseModel):
    locationid: int = Field
    saplocationcode: str = Field
    area: str = Field
    location: str = Field
