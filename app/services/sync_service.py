import logging
import os
import gspread
from datetime import datetime
from gspread.utils import rowcol_to_a1
from ..repositories.asset_repo import AssetRepository
from ..repositories.cycle_repo import CycleRepository

logger = logging.getLogger(__name__)


class GSheetSyncService:
    def __init__(self):

        self.CUSTOM_HEADERS = [
            "NO ASSET",
            "HBM",
            "NAMA ASET",
            "NAMA TEAM",
            "NILAI ASET (Rp)",
            "COST CENTER",
            "NOMOR SERI",
            "MODEL/TYPE",
            "MANUFACTURE",
            "GPS KOORDINAT",
            "KONDISI",
            "KODE LOKASI SAP",
            "AREA",
            "LOCATION",
            "LOKASI SPESIFIK PER-INVENTORY",
            "KETERANGAN",
            "HASIL INVENTORY",
            "TANGGAL INVENTORY",
            "PIC TEAM FAV",
        ]

        self.HEADER_MAP = {
            "NO ASSET": "assetnumber",
            "HBM": "hbm",
            "NAMA ASET": "assetname",
            "NAMA TEAM": "teamname",
            "NILAI ASET (Rp)": "assetvalue",
            "COST CENTER": "costcenter",
            "NOMOR SERI": "serialnumber",
            "MODEL/TYPE": "modeltype",
            "MANUFACTURE": "manufacturername",
            "GPS KOORDINAT": "gpscoordinate",
            "KONDISI": "conditionname",
            "KODE LOKASI SAP": "saplocationcode",
            "AREA": "area",
            "LOCATION": "location",
            "LOKASI SPESIFIK PER-INVENTORY": "specificlocation",
            "KETERANGAN": "description",
            "HASIL INVENTORY": "inventoryresult",
            "TANGGAL INVENTORY": "inventorydate",
            "PIC TEAM FAV": "picteamfav",
        }

        self.asset_repo = AssetRepository()
        self.cycle_repo = CycleRepository()

    def _get_client(self):
        base_dir = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        creds_path = os.path.join(base_dir, "credentials.json")
        if not os.path.exists(creds_path):
            logger.error(f"File credentials.json tidak ditemukan.")
            return None
        return gspread.service_account(filename=creds_path)

    def _format_row(self, index_no, asset_data):
        row = [index_no]
        for header_name in self.CUSTOM_HEADERS:
            key = self.HEADER_MAP.get(header_name)
            value = asset_data.get(key)
            formatted_value = ""

            if value is None:
                formatted_value = ""
            elif header_name == "NILAI ASET (Rp)":
                try:
                    formatted_value = f"{float(value):,.0f}".replace(",", ".")
                except (ValueError, TypeError):
                    formatted_value = str(value)
            elif key in ["inventorydate", "updatedat"]:

                if isinstance(value, datetime):
                    formatted_value = value.strftime("%d-%b-%Y")
                elif value:
                    try:

                        val_str = str(value)[:10]
                        dt = datetime.strptime(val_str, "%Y-%m-%d")
                        formatted_value = dt.strftime("%d-%b-%Y")
                    except (ValueError, TypeError):

                        formatted_value = str(value)
                else:
                    formatted_value = ""
            else:
                formatted_value = str(value)

            row.append(formatted_value)
        return row

    def _sync_sheet_content(self, worksheet, db_assets):
        sheet_data = worksheet.get_all_values()

        if not sheet_data or sheet_data[0] != ["NO"] + self.CUSTOM_HEADERS:
            worksheet.update("A1", [["NO"] + self.CUSTOM_HEADERS])
            sheet_data = worksheet.get_all_values()

        if len(sheet_data) <= 1:
            rows_to_write = []
            for i, asset in enumerate(db_assets, start=1):
                rows_to_write.append(self._format_row(i, asset))
            if rows_to_write:
                worksheet.append_rows(rows_to_write)
            return

        sheet_asset_map = {}
        for idx, row in enumerate(sheet_data[1:], start=2):
            if len(row) > 1:
                asset_no = str(row[1]).strip()
                if asset_no:
                    sheet_asset_map[asset_no] = {"row_idx": idx, "data": row}

        db_asset_numbers = set()
        updates = []
        new_rows = []
        last_no = len(sheet_data) - 1

        for asset in db_assets:
            db_asset_no = str(asset.get("assetnumber")).strip()
            db_asset_numbers.add(db_asset_no)

            formatted_row = self._format_row(0, asset)

            if db_asset_no in sheet_asset_map:
                existing = sheet_asset_map[db_asset_no]
                row_idx = existing["row_idx"]
                sheet_row_data = existing["data"]

                for col_idx in range(1, len(formatted_row)):
                    new_val = str(formatted_row[col_idx])
                    old_val = (
                        str(sheet_row_data[col_idx])
                        if col_idx < len(sheet_row_data)
                        else ""
                    )
                    if new_val != old_val:
                        updates.append(
                            {
                                "range": rowcol_to_a1(row_idx, col_idx + 1),
                                "values": [[new_val]],
                            }
                        )
            else:
                last_no += 1
                formatted_row[0] = last_no
                new_rows.append(formatted_row)

        if updates:
            worksheet.batch_update(updates)
        if new_rows:
            worksheet.append_rows(new_rows)

        rows_to_delete = []
        for asset_no, info in sheet_asset_map.items():
            if asset_no not in db_asset_numbers:
                rows_to_delete.append(info["row_idx"])

        if rows_to_delete:
            rows_to_delete.sort(reverse=True)
            for row_idx in rows_to_delete:
                worksheet.delete_rows(row_idx)
            logger.info(f"Menghapus {len(rows_to_delete)} baris data sampah di sheet.")

    def sync_master_data(self):
        client = self._get_client()
        if not client:
            return
        master_url = os.getenv("MASTER_SHEET_URL")
        if not master_url:
            return

        db_assets = self.asset_repo.get_all_export()

        try:
            sh = client.open_by_url(master_url)
            try:
                ws = sh.worksheet("MASTER-SHEET")
            except gspread.WorksheetNotFound:
                ws = sh.add_worksheet(title="MASTER-SHEET", rows=1000, cols=20)

            self._sync_sheet_content(ws, db_assets)
        except Exception as e:
            logger.error(f"Gagal Sync Master: {e}")

    def sync_cycle_data(self, year: int = None, cycle: int = None):
        periods_to_sync = []
        if year and cycle:
            periods_to_sync = [{"year": year, "cycle": cycle}]
        else:
            periods_to_sync = self.cycle_repo.get_periods()

        if not periods_to_sync:
            return
        client = self._get_client()
        if not client:
            return
        cycle_url = os.getenv("CYCLE_SHEET_URL")
        if not cycle_url:
            return

        try:
            sh = client.open_by_url(cycle_url)
            for p in periods_to_sync:
                c_num, y_num = p["cycle"], p["year"]
                sheet_title = f"CYCLE-{c_num}-YEAR-{y_num}"

                assets = self.cycle_repo.get_all_for_sync(y_num, c_num)

                try:
                    ws = sh.worksheet(sheet_title)
                except gspread.WorksheetNotFound:
                    ws = sh.add_worksheet(title=sheet_title, rows=1000, cols=20)

                self._sync_sheet_content(ws, assets)

        except Exception as e:
            logger.error(f"Gagal Sync Cycle: {e}")

    def delete_cycle_sheet(self, year: int, cycle: int):
        client = self._get_client()
        if not client:
            return
        cycle_url = os.getenv("CYCLE_SHEET_URL")
        try:
            sh = client.open_by_url(cycle_url)
            sheet_title = f"CYCLE-{cycle}-YEAR-{year}"
            try:
                ws = sh.worksheet(sheet_title)
                sh.del_worksheet(ws)
                logger.info(f"Sheet {sheet_title} berhasil dihapus.")
            except gspread.WorksheetNotFound:
                pass
        except Exception as e:
            logger.error(f"Gagal menghapus sheet cycle: {e}")