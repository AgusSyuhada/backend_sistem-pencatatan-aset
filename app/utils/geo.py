from geopy.geocoders import Nominatim
import logging

logger = logging.getLogger(__name__)


def get_city_from_coordinates(coordinates: str) -> str:
    try:
        if not coordinates or "," not in coordinates:
            return "Lokasi tidak diketahui"

        geolocator = Nominatim(user_agent="sipa_app_v1")
        location = geolocator.reverse(coordinates, timeout=10)

        if not location:
            return "Lokasi tidak diketahui"

        address = location.raw.get("address", {})

        city = (
            address.get("city")
            or address.get("town")
            or address.get("village")
            or address.get("county")
            or address.get("state")
        )
        return city if city else "Lokasi tidak diketahui"
    except Exception as e:
        logger.warning(
            f"Gagal mendapatkan lokasi dari koordinat {coordinates}: {str(e)}"
        )
        return "Lokasi terdeteksi"
