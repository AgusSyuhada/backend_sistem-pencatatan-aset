from typing import List, Optional, Tuple
from psycopg2 import extras
import psycopg2
from ..utils.db import db_connect, fetch_all_as_dict, fetch_one_as_dict

ASSET_MASTER_SELECT_QUERY = """
    SELECT 
        a.AssetNumber, a.HBM, a.SerialNumber, a.AssetName, a.ModelType,
        a.GPSCoordinate, a.SpecificLocation, a.Description, a.InventoryResult,
        cc.CostCenterCode AS CostCenter,
        l.SAPLocationCode,
        a.AssetValue, a.InventoryDate, a.IsActive,
        a.CreatedAt, a.UpdatedAt,
        t.TeamID, t.TeamName,
        m.ManufacturerID, m.ManufacturerName,
        c.ConditionID, c.ConditionName,
        l.LocationID, l.Area, l.Location,
        pics.picteamfav,
        photo_asset.PhotoURL AS assetphoto,
        photo_code.PhotoURL AS assetcodephoto,
        photo_loc.PhotoURL AS assetlocationphoto
    FROM sipa.MasterDataAsset a
    LEFT JOIN sipa.Teams t ON a.TeamID = t.TeamID
    LEFT JOIN sipa.Manufacturers m ON a.ManufacturerID = m.ManufacturerID
    LEFT JOIN sipa.Conditions c ON a.ConditionID = c.ConditionID
    LEFT JOIN sipa.Locations l ON a.LocationID = l.LocationID
    LEFT JOIN sipa.CostCenters cc ON a.CostCenterID = cc.CostCenterID
    LEFT JOIN (
        SELECT 
            aa.AssetNumber, 
            STRING_AGG(u.Name, ', ') AS picteamfav
        FROM sipa.AssetAssignments aa
        JOIN sipa.Users u ON aa.UserID = u.UserID
        WHERE aa.IsActive = TRUE
        GROUP BY aa.AssetNumber
    ) AS pics ON a.AssetNumber = pics.AssetNumber
    LEFT JOIN (
        SELECT DISTINCT ON (AssetNumber) AssetNumber, PhotoURL
        FROM sipa.AssetPhotos WHERE PhotoType = 'Asset' ORDER BY AssetNumber, CreatedAt DESC
    ) AS photo_asset ON a.AssetNumber = photo_asset.AssetNumber
    LEFT JOIN (
        SELECT DISTINCT ON (AssetNumber) AssetNumber, PhotoURL
        FROM sipa.AssetPhotos WHERE PhotoType = 'Code' ORDER BY AssetNumber, CreatedAt DESC
    ) AS photo_code ON a.AssetNumber = photo_code.AssetNumber
    LEFT JOIN (
        SELECT DISTINCT ON (AssetNumber) AssetNumber, PhotoURL
        FROM sipa.AssetPhotos WHERE PhotoType = 'Location' ORDER BY AssetNumber, CreatedAt DESC
    ) AS photo_loc ON a.AssetNumber = photo_loc.AssetNumber
"""


class AssetRepository:
    def get_all(
        self,
        q: str = None,
        include_inactive: bool = False,
        location_ids: List[int] = None,
        condition_ids: List[int] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> List[dict]:
        query = ASSET_MASTER_SELECT_QUERY
        conditions = []
        params = []

        if not include_inactive:
            conditions.append("a.IsActive = TRUE")

        if location_ids:
            conditions.append("a.LocationID = ANY(%s)")
            params.append(location_ids)

        if condition_ids:
            conditions.append("a.ConditionID = ANY(%s)")
            params.append(condition_ids)

        if q:
            search_q = f"%{q}%"
            conditions.append(
                """
                (COALESCE(a.AssetNumber, '') ILIKE %s OR 
                 COALESCE(a.AssetName, '') ILIKE %s OR 
                 COALESCE(a.SerialNumber, '') ILIKE %s OR
                 COALESCE(pics.picteamfav, '') ILIKE %s)
            """
            )
            params.extend([search_q, search_q, search_q, search_q])

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY a.AssetNumber ASC"
        query += " LIMIT %s OFFSET %s"
        params.extend([limit, offset])

        return fetch_all_as_dict(query, tuple(params))

    def get_all_export(self) -> List[dict]:
        query = (
            ASSET_MASTER_SELECT_QUERY
            + " WHERE a.IsActive = TRUE ORDER BY a.AssetNumber ASC"
        )
        return fetch_all_as_dict(query)

    def get_by_asset_number(self, asset_number: str) -> Optional[dict]:
        query = ASSET_MASTER_SELECT_QUERY + " WHERE a.AssetNumber = %s"
        return fetch_one_as_dict(query, (asset_number,))

    def _get_or_create_cost_center_id(self, cursor, code: str) -> Optional[int]:
        if not code:
            return None
        cursor.execute(
            "SELECT CostCenterID FROM sipa.CostCenters WHERE CostCenterCode = %s",
            (code,),
        )
        row = cursor.fetchone()
        if row:
            return row[0]
        cursor.execute(
            "INSERT INTO sipa.CostCenters (CostCenterCode) VALUES (%s) RETURNING CostCenterID",
            (code,),
        )
        return cursor.fetchone()[0]

    def create(
        self, asset_values: dict, creator_user_id: int, pic_user_ids: List[int] = None
    ) -> str:
        cc_code = asset_values.pop("CostCenter", None)

        conn = db_connect()
        try:
            with conn.cursor() as cursor:
                if cc_code:
                    cc_id = self._get_or_create_cost_center_id(cursor, cc_code)
                    asset_values["CostCenterID"] = cc_id

                cols = list(asset_values.keys())
                vals = list(asset_values.values())
                placeholders = ", ".join(["%s"] * len(cols))

                query_asset = f"INSERT INTO sipa.MasterDataAsset ({', '.join(cols)}) VALUES ({placeholders})"

                cursor.execute(query_asset, tuple(vals))
                asset_number = asset_values["AssetNumber"]

                final_pic_ids = set()
                if pic_user_ids:
                    final_pic_ids.update(pic_user_ids)

                final_pic_ids.add(creator_user_id)

                if final_pic_ids:
                    assignment_values = [
                        (asset_number, uid, True) for uid in final_pic_ids
                    ]
                    extras.execute_values(
                        cursor,
                        "INSERT INTO sipa.AssetAssignments (AssetNumber, UserID, IsActive) VALUES %s ON CONFLICT DO NOTHING",
                        assignment_values,
                    )

                conn.commit()
                return asset_number
        finally:
            conn.close()

    def update(
        self, asset_number: str, update_values: dict, pic_user_ids: List[int] = None
    ) -> bool:
        cc_code = update_values.pop("CostCenter", None)

        conn = db_connect()
        try:
            with conn.cursor() as cursor:
                if cc_code:
                    cc_id = self._get_or_create_cost_center_id(cursor, cc_code)
                    update_values["CostCenterID"] = cc_id

                if update_values:
                    set_clauses = [f"{k} = %s" for k in update_values.keys()]
                    set_clauses.append("UpdatedAt = CURRENT_TIMESTAMP")
                    vals = list(update_values.values()) + [asset_number]

                    query = f"UPDATE sipa.MasterDataAsset SET {', '.join(set_clauses)} WHERE AssetNumber = %s"
                    cursor.execute(query, tuple(vals))

                if pic_user_ids is not None:
                    cursor.execute(
                        """
                        DELETE FROM sipa.AssetAssignments 
                        WHERE AssetNumber = %s 
                          AND IsActive = FALSE 
                          AND UserID IN (
                              SELECT UserID 
                              FROM sipa.AssetAssignments 
                              WHERE AssetNumber = %s 
                                AND IsActive = TRUE
                          )
                    """,
                        (asset_number, asset_number),
                    )
                    
                    cursor.execute(
                        "UPDATE sipa.AssetAssignments SET IsActive = FALSE WHERE AssetNumber = %s",
                        (asset_number,),
                    )
                    
                    if pic_user_ids:
                        assignment_values = [
                            (asset_number, uid, True) for uid in pic_user_ids
                        ]
                        extras.execute_values(
                            cursor,
                            "INSERT INTO sipa.AssetAssignments (AssetNumber, UserID, IsActive) VALUES %s ON CONFLICT (AssetNumber, UserID, IsActive) DO NOTHING",
                            assignment_values,
                        )

                conn.commit()
                return True
        finally:
            conn.close()

    def set_active_status(self, asset_number: str, is_active: bool) -> bool:
        query = "UPDATE sipa.MasterDataAsset SET IsActive = %s, UpdatedAt = CURRENT_TIMESTAMP WHERE AssetNumber = %s"
        conn = db_connect()
        try:
            with conn.cursor() as cursor:
                cursor.execute(query, (is_active, asset_number))
                conn.commit()
                return cursor.rowcount > 0
        finally:
            conn.close()

    def get_user_ids_from_names(self, names: List[str]) -> List[int]:

        if not names:
            return []
        conn = db_connect()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT UserID FROM sipa.Users WHERE Name = ANY(%s)", (names,)
                )
                rows = cursor.fetchall()
                return [r[0] for r in rows]
        finally:
            conn.close()
