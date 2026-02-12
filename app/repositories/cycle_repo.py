from typing import List, Optional
from psycopg2 import extras
from ..utils.db import db_connect, fetch_all_as_dict, fetch_one_as_dict

ASSET_CYCLE_SELECT_QUERY = """
    SELECT 
        a.BackupID, a.Cycle, a.Year, a.AssetNumber, a.HBM, a.SerialNumber, 
        a.AssetName, a.ModelType, a.GPSCoordinate, a.SpecificLocation, 
        a.Description, a.InventoryResult, a.IsCycled,
        cc.CostCenterCode AS CostCenter,
        l.SAPLocationCode, 
        a.AssetValue, a.InventoryDate, a.CreatedAt, a.UpdatedAt, a.BackupTimestamp,
        t.TeamID, t.TeamName,
        m.ManufacturerID, m.ManufacturerName,
        c.ConditionID, c.ConditionName,
        l.LocationID, l.Area, l.Location,
        pics.picteamfav,
        photo_asset.PhotoURL AS assetphoto,
        photo_code.PhotoURL AS assetcodephoto,
        photo_loc.PhotoURL AS assetlocationphoto
    FROM sipa.AssetCycle a
    LEFT JOIN sipa.Teams t ON a.TeamID = t.TeamID
    LEFT JOIN sipa.Manufacturers m ON a.ManufacturerID = m.ManufacturerID
    LEFT JOIN sipa.Conditions c ON a.ConditionID = c.ConditionID
    LEFT JOIN sipa.Locations l ON a.LocationID = l.LocationID
    LEFT JOIN sipa.CostCenters cc ON a.CostCenterID = cc.CostCenterID
    LEFT JOIN (
        SELECT 
            aca.BackupID, 
            STRING_AGG(u.Name, ', ') AS picteamfav
        FROM sipa.AssetCycleAssignments aca
        JOIN sipa.Users u ON aca.UserID = u.UserID
        WHERE aca.IsActive = TRUE
        GROUP BY aca.BackupID
    ) AS pics ON a.BackupID = pics.BackupID
    LEFT JOIN (
        SELECT DISTINCT ON (BackupID) BackupID, PhotoURL
        FROM sipa.AssetPhotos WHERE PhotoType = 'Asset' AND BackupID IS NOT NULL
        ORDER BY BackupID, CreatedAt DESC
    ) AS photo_asset ON a.BackupID = photo_asset.BackupID
    LEFT JOIN (
        SELECT DISTINCT ON (BackupID) BackupID, PhotoURL
        FROM sipa.AssetPhotos WHERE PhotoType = 'Code' AND BackupID IS NOT NULL
        ORDER BY BackupID, CreatedAt DESC
    ) AS photo_code ON a.BackupID = photo_code.BackupID
    LEFT JOIN (
        SELECT DISTINCT ON (BackupID) BackupID, PhotoURL
        FROM sipa.AssetPhotos WHERE PhotoType = 'Location' AND BackupID IS NOT NULL
        ORDER BY BackupID, CreatedAt DESC
    ) AS photo_loc ON a.BackupID = photo_loc.BackupID
"""

ASSET_CYCLE_LIST_QUERY = """
    SELECT 
        a.AssetNumber, 
        a.AssetName, 
        c.ConditionName,
        l.Area, 
        l.Location,
        a.IsCycled
    FROM sipa.AssetCycle a
    LEFT JOIN sipa.Conditions c ON a.ConditionID = c.ConditionID
    LEFT JOIN sipa.Locations l ON a.LocationID = l.LocationID
"""


class CycleRepository:
    def get_periods(
        self, q: str = None, limit: int = 20, offset: int = 0
    ) -> List[dict]:

        query = """
            SELECT 
                Cycle, 
                Year, 
                COUNT(*) AS total_assets,
                COUNT(*) FILTER (WHERE IsCycled = TRUE) AS cycled_assets
            FROM sipa.AssetCycle 
            WHERE Year > 0
        """
        params = []

        if q and q.isdigit():
            q_int = int(q)
            query += " AND (Year = %s OR Cycle = %s)"
            params.extend([q_int, q_int])

        query += " GROUP BY Year, Cycle"
        query += " ORDER BY Year DESC, Cycle DESC"
        query += " LIMIT %s OFFSET %s"
        params.extend([limit, offset])

        results = fetch_all_as_dict(query, tuple(params))

        for row in results:
            total = row.get("total_assets", 0)
            cycled = row.get("cycled_assets", 0)
            row["percentage"] = (cycled / total * 100) if total > 0 else 0.0

        return results

    def check_exists(self, year: int, cycle: int) -> bool:
        if year == 0 and cycle == 0:
            return False

        conn = db_connect()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT 1 FROM sipa.AssetCycle WHERE Year = %s AND Cycle = %s LIMIT 1",
                    (year, cycle),
                )
                return cursor.fetchone() is not None
        finally:
            conn.close()

    def create_zero_cycle_entry(
        self, master_asset_data: dict, pic_user_ids: List[int] = None
    ) -> int:
        conn = db_connect()
        try:
            with conn.cursor() as cursor:
                columns = [
                    "Cycle",
                    "Year",
                    "AssetNumber",
                    "HBM",
                    "AssetName",
                    "TeamID",
                    "AssetValue",
                    "CostCenterID",
                    "SerialNumber",
                    "ModelType",
                    "ManufacturerID",
                    "GPSCoordinate",
                    "ConditionID",
                    "LocationID",
                    "SpecificLocation",
                    "Description",
                    "InventoryResult",
                    "InventoryDate",
                    "CreatedAt",
                    "UpdatedAt",
                    "IsCycled",
                ]

                asset_num = master_asset_data.get(
                    "assetnumber"
                ) or master_asset_data.get("AssetNumber")

                cursor.execute(
                    "SELECT * FROM sipa.MasterDataAsset WHERE AssetNumber = %s",
                    (asset_num,),
                )
                master_row = cursor.fetchone()
                if not master_row:
                    raise Exception(
                        "Master asset not found during cycle initialization"
                    )

                cols = [desc[0] for desc in cursor.description]
                raw_master = dict(zip(cols, master_row))

                values = (
                    0,  # Cycle
                    0,  # Year
                    raw_master.get("assetnumber"),
                    raw_master.get("hbm"),
                    raw_master.get("assetname"),
                    raw_master.get("teamid"),
                    raw_master.get("assetvalue"),
                    raw_master.get("costcenterid"),
                    raw_master.get("serialnumber"),
                    raw_master.get("modeltype"),
                    raw_master.get("manufacturerid"),
                    raw_master.get("gpscoordinate"),
                    raw_master.get("conditionid"),
                    raw_master.get("locationid"),
                    raw_master.get("specificlocation"),
                    raw_master.get("description"),
                    raw_master.get("inventoryresult"),
                    raw_master.get("inventorydate"),
                    raw_master.get("createdat"),
                    raw_master.get("updatedat"),
                    False,  # IsCycled
                )

                query = f"""
                    INSERT INTO sipa.AssetCycle ({', '.join(columns)})
                    VALUES ({', '.join(['%s'] * len(columns))})
                    ON CONFLICT (Year, Cycle, AssetNumber) 
                    DO UPDATE SET UpdatedAt = EXCLUDED.UpdatedAt
                    RETURNING BackupID
                """

                cursor.execute(query, values)
                backup_id = cursor.fetchone()[0]

                if pic_user_ids:
                    cursor.execute(
                        """
                        DELETE FROM sipa.AssetCycleAssignments 
                        WHERE BackupID = %s 
                          AND IsActive = FALSE 
                          AND UserID IN (
                              SELECT UserID 
                              FROM sipa.AssetCycleAssignments 
                              WHERE BackupID = %s 
                                AND IsActive = TRUE
                          )
                    """,
                        (backup_id, backup_id),
                    )

                    cursor.execute(
                        "UPDATE sipa.AssetCycleAssignments SET IsActive = FALSE WHERE BackupID = %s",
                        (backup_id,),
                    )

                    assignment_values = [(backup_id, uid, True) for uid in pic_user_ids]
                    extras.execute_values(
                        cursor,
                        "INSERT INTO sipa.AssetCycleAssignments (BackupID, UserID, IsActive) VALUES %s ON CONFLICT DO NOTHING",
                        assignment_values,
                    )

                conn.commit()
                return backup_id

        finally:
            conn.close()

    def copy_master_to_cycle(self, asset_numbers: List[str], year: int, cycle: int):
        if not asset_numbers:
            return

        conn = db_connect()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM sipa.MasterDataAsset WHERE AssetNumber = ANY(%s)",
                    (asset_numbers,),
                )
                if cursor.rowcount == 0:
                    return

                cols = [desc[0].lower() for desc in cursor.description]
                master_rows = cursor.fetchall()
                master_assets = [dict(zip(cols, row)) for row in master_rows]

                cycle_values = []
                for asset in master_assets:
                    cycle_values.append(
                        (
                            cycle,
                            year,
                            asset["assetnumber"],
                            asset["hbm"],
                            asset["assetname"],
                            asset["teamid"],
                            asset["assetvalue"],
                            asset["costcenterid"],
                            asset["serialnumber"],
                            asset["modeltype"],
                            asset["manufacturerid"],
                            asset["gpscoordinate"],
                            asset["conditionid"],
                            asset["locationid"],
                            asset["specificlocation"],
                            asset["description"],
                            asset["inventoryresult"],
                            asset["inventorydate"],
                            asset["createdat"],
                            asset["updatedat"],
                            False,  # IsCycled initial value
                        )
                    )

                query_insert = """
                    INSERT INTO sipa.AssetCycle (
                        Cycle, Year, AssetNumber, HBM, AssetName, TeamID, AssetValue, CostCenterID,
                        SerialNumber, ModelType, ManufacturerID, GPSCoordinate, ConditionID,
                        LocationID, SpecificLocation, Description, InventoryResult, InventoryDate, 
                        CreatedAt, UpdatedAt, IsCycled
                    ) VALUES %s RETURNING BackupID, AssetNumber
                """

                extras.execute_values(
                    cursor, query_insert, cycle_values, page_size=100, fetch=True
                )
                inserted = cursor.fetchall()

                backup_map = {row[1]: row[0] for row in inserted}

                cursor.execute(
                    "SELECT AssetNumber, UserID FROM sipa.AssetAssignments WHERE AssetNumber = ANY(%s) AND IsActive = TRUE",
                    (asset_numbers,),
                )
                pics = cursor.fetchall()

                cycle_pics = []
                for asset_num, user_id in pics:
                    if asset_num in backup_map:
                        cycle_pics.append((backup_map[asset_num], user_id, True))

                if cycle_pics:
                    extras.execute_values(
                        cursor,
                        "INSERT INTO sipa.AssetCycleAssignments (BackupID, UserID, IsActive) VALUES %s",
                        cycle_pics,
                    )

                conn.commit()
        finally:
            conn.close()

    def get_by_period(
        self,
        year: int,
        cycle: int,
        q: str = None,
        location_ids: List[int] = None,
        condition_ids: List[int] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> List[dict]:
        query = ASSET_CYCLE_LIST_QUERY + " WHERE a.Year = %s AND a.Cycle = %s"
        params = [year, cycle]

        if location_ids:
            query += " AND a.LocationID = ANY(%s)"
            params.append(location_ids)

        if condition_ids:
            query += " AND a.ConditionID = ANY(%s)"
            params.append(condition_ids)

        if q:
            search_q = f"%{q}%"
            query += " AND (COALESCE(a.AssetNumber, '') ILIKE %s OR COALESCE(a.AssetName, '') ILIKE %s)"
            params.extend([search_q, search_q])

        query += " ORDER BY a.AssetNumber"
        query += " LIMIT %s OFFSET %s"
        params.extend([limit, offset])

        return fetch_all_as_dict(query, tuple(params))

    def get_all_for_sync(self, year: int, cycle: int) -> List[dict]:
        query = (
            ASSET_CYCLE_SELECT_QUERY
            + " WHERE a.Year = %s AND a.Cycle = %s ORDER BY a.AssetNumber"
        )
        return fetch_all_as_dict(query, (year, cycle))

    def get_single_cycle_asset(
        self, year: int, cycle: int, asset_number: str
    ) -> Optional[dict]:
        query = (
            ASSET_CYCLE_SELECT_QUERY
            + " WHERE a.Year = %s AND a.Cycle = %s AND a.AssetNumber = %s"
        )
        return fetch_one_as_dict(query, (year, cycle, asset_number))

    def update_cycle_asset(
        self, backup_id: int, update_values: dict, pic_user_ids: List[int] = None
    ) -> bool:
        update_values.pop("CostCenter", None)
        update_values.pop("SAPLocationCode", None)

        conn = db_connect()
        try:
            with conn.cursor() as cursor:
                if update_values:
                    set_clauses = [f"{k} = %s" for k in update_values.keys()]
                    set_clauses.append("UpdatedAt = CURRENT_TIMESTAMP")
                    set_clauses.append("IsCycled = TRUE")

                    vals = list(update_values.values()) + [backup_id]
                    cursor.execute(
                        f"UPDATE sipa.AssetCycle SET {', '.join(set_clauses)} WHERE BackupID = %s",
                        tuple(vals),
                    )

                if pic_user_ids is not None:
                    cursor.execute(
                        """
                        DELETE FROM sipa.AssetCycleAssignments 
                        WHERE BackupID = %s 
                          AND IsActive = FALSE 
                          AND UserID IN (
                              SELECT UserID 
                              FROM sipa.AssetCycleAssignments 
                              WHERE BackupID = %s 
                                AND IsActive = TRUE
                          )
                        """,
                        (backup_id, backup_id),
                    )

                    cursor.execute(
                        "UPDATE sipa.AssetCycleAssignments SET IsActive = FALSE WHERE BackupID = %s",
                        (backup_id,),
                    )

                    if pic_user_ids:
                        vals = [(backup_id, uid, True) for uid in pic_user_ids]
                        extras.execute_values(
                            cursor,
                            "INSERT INTO sipa.AssetCycleAssignments (BackupID, UserID, IsActive) VALUES %s ON CONFLICT DO NOTHING",
                            vals,
                        )

                conn.commit()
                return True
        finally:
            conn.close()

    def delete_assets_from_cycle(
        self, year: int, cycle: int, asset_numbers: List[str]
    ) -> bool:
        if not asset_numbers:
            return False
        conn = db_connect()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "DELETE FROM sipa.AssetCycle WHERE Year = %s AND Cycle = %s AND AssetNumber = ANY(%s)",
                    (year, cycle, asset_numbers),
                )
                conn.commit()
                return cursor.rowcount > 0
        finally:
            conn.close()

    def delete_period(self, year: int, cycle: int) -> bool:
        conn = db_connect()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "DELETE FROM sipa.AssetCycle WHERE Year = %s AND Cycle = %s",
                    (year, cycle),
                )
                conn.commit()
                return cursor.rowcount > 0
        finally:
            conn.close()

    def get_statistics(self, year: int, cycle: int) -> dict:
        conn = db_connect()
        try:
            with conn.cursor() as cursor:

                cursor.execute(
                    """
                    SELECT 
                        COUNT(*) as total,
                        COUNT(*) FILTER (WHERE IsCycled = TRUE) as cycled,
                        COUNT(*) FILTER (WHERE IsCycled = FALSE) as pending,
                        COALESCE(SUM(AssetValue), 0) as total_value
                    FROM sipa.AssetCycle 
                    WHERE Year = %s AND Cycle = %s
                    """,
                    (year, cycle),
                )
                summary_row = cursor.fetchone()
                total = summary_row[0]

                if total == 0:
                    return None

                summary = {
                    "total_assets": total,
                    "cycled_assets": summary_row[1],
                    "pending_assets": summary_row[2],
                    "completion_percentage": (
                        round((summary_row[1] / total * 100), 2) if total > 0 else 0
                    ),
                    "total_asset_value": float(summary_row[3]),
                }

                def fetch_distribution(query, params):
                    cursor.execute(query, params)
                    rows = cursor.fetchall()
                    return [
                        {
                            "name": str(row[0]) if row[0] is not None else "Unknown",
                            "count": row[1],
                            "percentage": round((row[1] / total * 100), 2),
                        }
                        for row in rows
                    ]

                by_condition = fetch_distribution(
                    """
                    SELECT COALESCE(c.ConditionName, 'N/A'), COUNT(a.AssetNumber)
                    FROM sipa.AssetCycle a
                    LEFT JOIN sipa.Conditions c ON a.ConditionID = c.ConditionID
                    WHERE a.Year = %s AND a.Cycle = %s
                    GROUP BY c.ConditionName ORDER BY COUNT(a.AssetNumber) DESC
                    """,
                    (year, cycle),
                )

                by_team = fetch_distribution(
                    """
                    SELECT COALESCE(t.TeamName, 'Unassigned'), COUNT(a.AssetNumber)
                    FROM sipa.AssetCycle a
                    LEFT JOIN sipa.Teams t ON a.TeamID = t.TeamID
                    WHERE a.Year = %s AND a.Cycle = %s
                    GROUP BY t.TeamName ORDER BY COUNT(a.AssetNumber) DESC
                    """,
                    (year, cycle),
                )

                by_area = fetch_distribution(
                    """
                    SELECT COALESCE(l.Area, 'No Area'), COUNT(a.AssetNumber)
                    FROM sipa.AssetCycle a
                    LEFT JOIN sipa.Locations l ON a.LocationID = l.LocationID
                    WHERE a.Year = %s AND a.Cycle = %s
                    GROUP BY l.Area ORDER BY COUNT(a.AssetNumber) DESC
                    """,
                    (year, cycle),
                )

                by_result = fetch_distribution(
                    """
                    SELECT COALESCE(InventoryResult, 'Not Yet Checked'), COUNT(AssetNumber)
                    FROM sipa.AssetCycle
                    WHERE Year = %s AND Cycle = %s
                    GROUP BY InventoryResult ORDER BY COUNT(AssetNumber) DESC
                    """,
                    (year, cycle),
                )

                by_manufacturer = fetch_distribution(
                    """
                    SELECT COALESCE(m.ManufacturerName, 'Generic/Unknown'), COUNT(a.AssetNumber)
                    FROM sipa.AssetCycle a
                    LEFT JOIN sipa.Manufacturers m ON a.ManufacturerID = m.ManufacturerID
                    WHERE a.Year = %s AND a.Cycle = %s
                    GROUP BY m.ManufacturerName ORDER BY COUNT(a.AssetNumber) DESC
                    """,
                    (year, cycle),
                )

                by_cost_center = fetch_distribution(
                    """
                    SELECT COALESCE(cc.CostCenterCode, 'N/A'), COUNT(a.AssetNumber)
                    FROM sipa.AssetCycle a
                    LEFT JOIN sipa.CostCenters cc ON a.CostCenterID = cc.CostCenterID
                    WHERE a.Year = %s AND a.Cycle = %s
                    GROUP BY cc.CostCenterCode ORDER BY COUNT(a.AssetNumber) DESC
                    """,
                    (year, cycle),
                )

                cursor.execute(
                    """
                    SELECT DATE(InventoryDate) as log_date, COUNT(*)
                    FROM sipa.AssetCycle
                    WHERE Year = %s AND Cycle = %s AND IsCycled = TRUE AND InventoryDate IS NOT NULL
                    GROUP BY log_date ORDER BY log_date ASC
                    """,
                    (year, cycle),
                )
                timeline = [
                    {"date": str(row[0]), "count": row[1]} for row in cursor.fetchall()
                ]

                return {
                    "message": "Statistik periode berhasil disusun secara mendalam.",
                    "year": year,
                    "cycle": cycle,
                    "summary": summary,
                    "distributions": {
                        "condition": by_condition,
                        "team": by_team,
                        "area": by_area,
                        "inventory_result": by_result,
                        "manufacturer": by_manufacturer,
                        "cost_center": by_cost_center,
                    },
                    "timeline": timeline,
                }
        finally:
            conn.close()

    def get_backup_id(self, asset_number: str, year: int, cycle: int):
        conn = db_connect()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT BackupID FROM sipa.AssetCycle WHERE AssetNumber = %s AND Year = %s AND Cycle = %s",
                    (asset_number, year, cycle),
                )
                row = cursor.fetchone()
                return row[0] if row else None
        finally:
            conn.close()

    def add_asset_photo(
        self,
        asset_number: str,
        year: int,
        cycle: int,
        backup_id: int,
        photo_type: str,
        photo_url: str,
    ):
        conn = db_connect()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO sipa.AssetPhotos 
                    (AssetNumber, Cycle, Year, BackupID, PhotoType, PhotoURL)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (asset_number, cycle, year, backup_id, photo_type, photo_url),
                )
                conn.commit()
        finally:
            conn.close()

    def get_latest_period(self) -> Optional[dict]:
        conn = db_connect()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT Cycle, Year FROM sipa.AssetCycle ORDER BY Year DESC, Cycle DESC LIMIT 1"
                )
                row = cursor.fetchone()
                if row:
                    return {"cycle": row[0], "year": row[1]}
                return None
        finally:
            conn.close()

    def is_asset_in_cycle(self, asset_number: str, year: int, cycle: int) -> bool:
        conn = db_connect()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT 1 FROM sipa.AssetCycle WHERE AssetNumber = %s AND Year = %s AND Cycle = %s",
                    (asset_number, year, cycle),
                )
                return cursor.fetchone() is not None
        finally:
            conn.close()

    def update_from_master_sync(
        self,
        asset_number: str,
        year: int,
        cycle: int,
        master_db_data: dict,
        pic_user_ids: List[int] = None,
    ):
        conn = db_connect()
        try:
            with conn.cursor() as cursor:

                if master_db_data:
                    master_db_data.pop("CostCenter", None)
                    master_db_data.pop("SAPLocationCode", None)

                set_clauses = []
                vals = []

                if master_db_data:
                    set_clauses = [f"{k} = %s" for k in master_db_data.keys()]
                    vals = list(master_db_data.values())

                set_clauses.append("UpdatedAt = CURRENT_TIMESTAMP")
                set_clauses.append("IsCycled = TRUE")

                vals.extend([asset_number, year, cycle])

                query = f"""
                    UPDATE sipa.AssetCycle 
                    SET {', '.join(set_clauses)} 
                    WHERE AssetNumber = %s AND Year = %s AND Cycle = %s
                    RETURNING BackupID
                """
                cursor.execute(query, tuple(vals))
                row = cursor.fetchone()

                if row:
                    backup_id = row[0]

                    if pic_user_ids is not None:
                        cursor.execute(
                            """
                            DELETE FROM sipa.AssetCycleAssignments 
                            WHERE BackupID = %s 
                              AND IsActive = FALSE 
                              AND UserID IN (
                                  SELECT UserID 
                                  FROM sipa.AssetCycleAssignments 
                                  WHERE BackupID = %s 
                                    AND IsActive = TRUE
                              )
                        """,
                            (backup_id, backup_id),
                        )

                        cursor.execute(
                            "UPDATE sipa.AssetCycleAssignments SET IsActive = FALSE WHERE BackupID = %s",
                            (backup_id,),
                        )

                        if pic_user_ids:
                            assignment_values = [
                                (backup_id, uid, True) for uid in pic_user_ids
                            ]
                            extras.execute_values(
                                cursor,
                                "INSERT INTO sipa.AssetCycleAssignments (BackupID, UserID, IsActive) VALUES %s",
                                assignment_values,
                            )
                conn.commit()
        finally:
            conn.close()

    def get_all_assets_by_period(self, year: int, cycle: int) -> List[dict]:
        query = (
            ASSET_CYCLE_SELECT_QUERY
            + " WHERE a.Year = %s AND a.Cycle = %s ORDER BY a.AssetNumber"
        )
        return fetch_all_as_dict(query, (year, cycle))

    def get_all_for_sync(self, year: int, cycle: int) -> List[dict]:
        return self.get_all_assets_by_period(year, cycle)
