import os
import logging
from fastapi import UploadFile
from azure.storage.blob import BlobServiceClient, generate_blob_sas, BlobSasPermissions, ContentSettings
from azure.core.exceptions import AzureError, ResourceNotFoundError
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

def _get_blob_service_client():
    blob_connection_string = os.getenv("BLOB_CONNECTION_STRING")
    if not blob_connection_string:
        logger.error("BLOB_CONNECTION_STRING tidak di-set.")
        return None
    try:
        return BlobServiceClient.from_connection_string(blob_connection_string)
    except ValueError as e:
        logger.error(f"Connection string Azure Blob tidak valid: {e}")
        return None

def upload_file_to_blob(file: UploadFile, blob_path: str, content_type: str) -> str | None:
    container_name = os.getenv("BLOB_CONTAINER_NAME")
    if not container_name:
        logger.error("BLOB_CONTAINER_NAME tidak di-set.")
        return None

    blob_service_client = _get_blob_service_client()
    if not blob_service_client:
        return None

    try:
        blob_client = blob_service_client.get_blob_client(
            container=container_name, blob=blob_path
        )

        file.file.seek(0)
        file_data = file.file.read()
        
        settings = ContentSettings(content_type=content_type)
        blob_client.upload_blob(file_data, overwrite=True, content_settings=settings)

        logger.info(f"File berhasil diunggah: {container_name}/{blob_path}")
        return blob_path

    except AzureError as e:
        logger.error(f"Azure Error saat upload {blob_path}: {e}", exc_info=True)
        return None
    except Exception as e:
        logger.error(f"Unexpected Error saat upload {blob_path}: {e}", exc_info=True)
        return None

def delete_blob(blob_path: str) -> bool:
    container_name = os.getenv("BLOB_CONTAINER_NAME")
    if not container_name or not blob_path:
        return False

    blob_service_client = _get_blob_service_client()
    if not blob_service_client:
        return False

    try:
        blob_client = blob_service_client.get_blob_client(
            container=container_name, blob=blob_path
        )
        blob_client.delete_blob()
        logger.info(f"Blob dihapus: {blob_path}")
        return True
    except ResourceNotFoundError:
        logger.warning(f"Blob tidak ditemukan (sudah terhapus?): {blob_path}")
        return True
    except AzureError as e:
        logger.error(f"Gagal menghapus blob {blob_path}: {e}", exc_info=True)
        return False

def generate_sas_url(blob_path: str) -> str | None:
    if not blob_path:
        return None

    container_name = os.getenv("BLOB_CONTAINER_NAME")
    blob_service_client = _get_blob_service_client()

    if not container_name or not blob_service_client:
        return None

    try:
        sas_token = generate_blob_sas(
            account_name=blob_service_client.account_name,
            container_name=container_name,
            blob_name=blob_path,
            account_key=blob_service_client.credential.account_key,
            permission=BlobSasPermissions(read=True),
            expiry=datetime.now(timezone.utc) + timedelta(hours=1),
        )
        
        return f"{blob_service_client.url}{container_name}/{blob_path}?{sas_token}"

    except Exception as e:
        logger.error(f"Gagal generate SAS URL untuk {blob_path}: {e}")
        return None