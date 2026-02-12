import logging
from datetime import datetime
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv
from .routers import auth, users, ocr
from .routers import assets_master, assets_cycle
from .routers import lookup
from .schemas.common_schema import ErrorResponse
from .utils.db import db_connect, fetch_all_as_dict
from pytz import timezone
import gspread
from .services.sync_service import GSheetSyncService
import threading


load_dotenv()


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={"message": exc.detail})


app = FastAPI(title="SIPA API", version="1.0.0")

scheduler = BackgroundScheduler()


@app.on_event("startup")
def start_scheduler():
    wib_tz = timezone("Asia/Jakarta")

    scheduler.start()
    logger.info("Scheduler telah dimulai.")

    def run_startup_sync():
        logger.info("Menjalankan Initial Backup ke Google Sheet via Service...")
        sync_service = GSheetSyncService()

        try:
            sync_service.sync_master_data()
            sync_service.sync_cycle_data()
        except Exception as e:
            logger.error(f"Gagal menjalankan startup sync: {e}")

    startup_thread = threading.Thread(target=run_startup_sync)
    startup_thread.start()


@app.on_event("shutdown")
def shutdown_scheduler():
    scheduler.shutdown()
    logger.info("Scheduler telah dimatikan.")


app.add_exception_handler(HTTPException, http_exception_handler)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(assets_cycle.router)
app.include_router(assets_master.router)
app.include_router(ocr.router)
app.include_router(lookup.router)


@app.get("/", tags=["Root"])
def read_root():
    return {"message": "Welcome to the Sistem Pencatatan Aset API!"}
