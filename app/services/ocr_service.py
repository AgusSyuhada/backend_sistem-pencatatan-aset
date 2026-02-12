import os
import time
import requests
import re
from fastapi import HTTPException


class OcrService:
    def __init__(self):
        self.endpoint = os.getenv("AZURE_VISION_ENDPOINT")
        self.key = os.getenv("AZURE_VISION_KEY")

    def _parse_ocr_result(self, json_response: dict) -> tuple:
        all_text = []
        analyze_result = json_response.get("analyzeResult")
        if not analyze_result:
            return None, all_text

        read_results = analyze_result.get("readResults", [])
        for page in read_results:
            lines = page.get("lines", [])
            for line in lines:
                text = line.get("text", "")
                all_text.append(text)
                lower_text = text.lower()

                if "hbm" in lower_text and ":" in lower_text:
                    hbm_number = re.sub(r"[^0-9]", "", text)
                    if len(hbm_number) >= 6:
                        return hbm_number[-6:], all_text

                potential = re.sub(r"[\s.-]", "", text)
                if re.match(r"^[0-9]{9,}$", potential):
                    return potential[-6:], all_text

        return None, all_text

    def process_image(self, image_bytes: bytes) -> tuple:
        if not all([self.endpoint, self.key]):
            raise HTTPException(
                status_code=500, detail="Konfigurasi server OCR missing."
            )

        api_url = f"{self.endpoint}vision/v3.2/read/analyze"
        headers = {
            "Ocp-Apim-Subscription-Key": self.key,
            "Content-Type": "application/octet-stream",
        }

        try:
            response = requests.post(api_url, headers=headers, data=image_bytes)
            response.raise_for_status()
        except requests.RequestException as e:
            raise HTTPException(status_code=503, detail=f"OCR Service Error: {e}")

        op_url = response.headers.get("operation-location")
        if not op_url:
            raise HTTPException(status_code=500, detail="Invalid OCR response.")

        for _ in range(10):
            res = requests.get(op_url, headers=headers)
            if res.status_code != 200:
                raise HTTPException(
                    status_code=500, detail="Failed to fetch OCR result."
                )

            data = res.json()
            status = data.get("status")

            if status == "succeeded":
                return self._parse_ocr_result(data)
            if status == "failed":
                raise HTTPException(status_code=500, detail="OCR processing failed.")

            time.sleep(1)

        raise HTTPException(status_code=408, detail="OCR Timeout.")
