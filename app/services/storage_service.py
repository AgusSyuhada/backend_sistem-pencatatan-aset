from typing import List, Union, Any
from ..utils.blob_storage import generate_sas_url


class StorageService:
    @staticmethod
    def attach_sas_urls(data: Union[dict, List[dict]]) -> Union[dict, List[dict]]:
        if not data:
            return data

        is_list = isinstance(data, list)
        items = data if is_list else [data]

        for item in items:
            if item.get("assetphoto"):
                item["assetphoto"] = generate_sas_url(item["assetphoto"])
            if item.get("assetcodephoto"):
                item["assetcodephoto"] = generate_sas_url(item["assetcodephoto"])
            if item.get("assetlocationphoto"):
                item["assetlocationphoto"] = generate_sas_url(
                    item["assetlocationphoto"]
                )

        return items if is_list else items[0]
