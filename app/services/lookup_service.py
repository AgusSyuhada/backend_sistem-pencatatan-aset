from fastapi import HTTPException, status
from ..repositories.lookup_repo import LookupRepository


class LookupService:
    def __init__(self):
        self.repo = LookupRepository()

    def get_roles(self):
        return self.repo.get_roles()

    def get_teams(self, q: str = None):
        return self.repo.get_teams(q)

    def create_team(self, team_name: str):
        try:
            return self.repo.create_team(team_name)
        except Exception as e:
            if "unique" in str(e).lower():
                raise HTTPException(status_code=409, detail="Nama Team sudah ada.")
            raise e

    def get_manufacturers(self, q: str = None):
        return self.repo.get_manufacturers(q)

    def create_manufacturer(self, name: str):
        try:
            return self.repo.create_manufacturer(name)
        except Exception as e:
            if "unique" in str(e).lower():
                raise HTTPException(
                    status_code=409, detail="Nama Manufacturer sudah ada."
                )
            raise e

    def get_conditions(self, q: str = None):
        return self.repo.get_conditions(q)

    def get_cost_centers(self, q: str = None):
        return self.repo.get_cost_centers(q)

    def create_cost_center(self, code: str):
        try:
            return self.repo.create_cost_center(code)
        except Exception as e:
            if "unique" in str(e).lower():
                raise HTTPException(
                    status_code=409, detail="Kode Cost Center sudah ada."
                )
            raise e

    def get_locations(self, area_q: str = None, location_q: str = None):
        return self.repo.get_locations(area_q, location_q)

    def create_location(self, sap_code: str, area: str, location: str):
        try:
            return self.repo.create_location(sap_code, area, location)
        except Exception as e:
            if "unique" in str(e).lower():
                raise HTTPException(
                    status_code=409,
                    detail=f"Lokasi '{location}' di Area '{area}' (SAP: {sap_code}) sudah terdaftar.",
                )
            raise HTTPException(status_code=500, detail=str(e))

