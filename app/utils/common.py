import random
import string
from datetime import datetime
import pytz

WIB = pytz.timezone("Asia/Jakarta")


def get_current_time_wib() -> datetime:
    return datetime.now(WIB)


def format_display_time(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = pytz.utc.localize(dt).astimezone(WIB)
    return dt.strftime("%H:%M %d-%m-%Y")


def generate_numeric_otp(length: int = 6) -> str:
    return "".join(random.choices(string.digits, k=length))
