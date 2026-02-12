from typing import List
from ..utils.db import fetch_all_as_dict, db_connect


class LookupRepository:
    def get_roles(self) -> List[dict]:
        query = "SELECT RoleID, RoleName FROM sipa.Roles ORDER BY RoleName ASC"
        return fetch_all_as_dict(query)

    def get_teams(self, q: str = None) -> List[dict]:
        query = "SELECT TeamID, TeamName FROM sipa.Teams"
        params = []

        if q:
            query += " WHERE TeamName ILIKE %s"
            params.append(f"%{q}%")

        query += " ORDER BY TeamName ASC"
        return fetch_all_as_dict(query, tuple(params))

    def create_team(self, team_name: str) -> dict:
        conn = db_connect()
        try:
            with conn.cursor() as cursor:
                query = "INSERT INTO sipa.Teams (TeamName) VALUES (%s) RETURNING TeamID, TeamName"
                cursor.execute(query, (team_name,))
                conn.commit()
                row = cursor.fetchone()
                return {"teamid": row[0], "teamname": row[1]}
        finally:
            conn.close()

    def get_manufacturers(self, q: str = None) -> List[dict]:
        query = "SELECT ManufacturerID, ManufacturerName FROM sipa.Manufacturers"
        params = []

        if q:
            query += " WHERE ManufacturerName ILIKE %s"
            params.append(f"%{q}%")

        query += " ORDER BY ManufacturerName ASC"
        return fetch_all_as_dict(query, tuple(params))

    def create_manufacturer(self, name: str) -> dict:
        conn = db_connect()
        try:
            with conn.cursor() as cursor:
                query = "INSERT INTO sipa.Manufacturers (ManufacturerName) VALUES (%s) RETURNING ManufacturerID, ManufacturerName"
                cursor.execute(query, (name,))
                conn.commit()
                row = cursor.fetchone()
                return {"manufacturerid": row[0], "manufacturername": row[1]}
        finally:
            conn.close()

    def get_conditions(self, q: str = None) -> List[dict]:
        query = "SELECT ConditionID, ConditionName FROM sipa.Conditions"
        params = []

        if q:
            query += " WHERE ConditionName ILIKE %s"
            params.append(f"%{q}%")

        query += " ORDER BY ConditionID ASC"
        return fetch_all_as_dict(query, tuple(params))

    def get_cost_centers(self, q: str = None) -> List[dict]:
        query = "SELECT CostCenterID, CostCenterCode FROM sipa.CostCenters"
        params = []
        if q:
            query += " WHERE CostCenterCode ILIKE %s"
            params.append(f"%{q}%")
        query += " ORDER BY CostCenterCode ASC"
        return fetch_all_as_dict(query, tuple(params))

    def create_cost_center(self, code: str) -> dict:
        conn = db_connect()
        try:
            with conn.cursor() as cursor:
                query = "INSERT INTO sipa.CostCenters (CostCenterCode) VALUES (%s) RETURNING CostCenterID, CostCenterCode"
                cursor.execute(query, (code,))
                conn.commit()
                row = cursor.fetchone()
                return {"costcenterid": row[0], "costcentercode": row[1]}
        finally:
            conn.close()

    def get_locations(self, area_q: str = None, location_q: str = None) -> List[dict]:
        query = """
            SELECT LocationID, SAPLocationCode, Area, Location 
            FROM sipa.Locations 
        """
        conditions = []
        params = []

        if area_q:
            conditions.append("Area ILIKE %s")
            params.append(f"%{area_q}%")

        if location_q:
            conditions.append("Location ILIKE %s")
            params.append(f"%{location_q}%")

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY Area ASC, Location ASC"
        return fetch_all_as_dict(query, tuple(params))

    def create_location(self, sap_code: str, area: str, location: str) -> dict:
        conn = db_connect()
        try:
            with conn.cursor() as cursor:
                query = """
                    INSERT INTO sipa.Locations (SAPLocationCode, Area, Location) 
                    VALUES (%s, %s, %s) 
                    RETURNING LocationID, SAPLocationCode, Area, Location
                """
                cursor.execute(query, (sap_code, area, location))
                conn.commit()
                row = cursor.fetchone()
                return {
                    "locationid": row[0],
                    "saplocationcode": row[1],
                    "area": row[2],
                    "location": row[3],
                }
        finally:
            conn.close()