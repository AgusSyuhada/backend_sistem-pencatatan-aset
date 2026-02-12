import os
from datetime import datetime, timezone
from fastapi import HTTPException, UploadFile, status
from ..utils.blob_storage import upload_file_to_blob, delete_blob


class UploadService:
    def validate_image(self, file: UploadFile):
        allowed = ["image/jpeg", "image/png", "image/webp"]
        if file.content_type not in allowed:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail="Format file tidak didukung. Mohon gunakan format JPG, PNG, atau WebP.",
            )

    def upload_profile_picture(self, file: UploadFile, user_id: int) -> str:
        self.validate_image(file)
        ext = os.path.splitext(file.filename)[1]
        blob_path = f"profilepictures/{user_id}{ext}"

        url = upload_file_to_blob(file, blob_path, file.content_type)
        if not url:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Gagal upload ke storage.",
            )
        return url

    def upload_asset_photo(
        self,
        file: UploadFile,
        asset_number: str,
        year: int,
        cycle: int,
        photo_type: str,
    ) -> str:
        self.validate_image(file)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        ext = os.path.splitext(file.filename)[1]

        blob_filename = f"{photo_type}_{year}_{cycle}_{timestamp}{ext}"
        blob_path = f"assetphotos/{asset_number}/{blob_filename}"

        url = upload_file_to_blob(file, blob_path, file.content_type)
        if not url:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Gagal upload ke storage.",
            )
        return url

    def delete_old_file(self, blob_path: str):
        if blob_path:
            delete_blob(blob_path)
