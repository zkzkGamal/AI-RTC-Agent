# core/auth.py
import datetime
import math
import time
from zoneinfo import ZoneInfo

class api_key_generator:
    def __init__(self, expire_time: int = 60):
        self.expire_time = expire_time
        self.time_zone = "UTC"

    def get_date_timestamp(self, input_type: str = "date"):
        now_utc = datetime.datetime.now(tz=ZoneInfo("UTC"))
        country_tz = now_utc.astimezone(ZoneInfo(self.time_zone))
        if input_type == "date":
            return country_tz.date()
        return country_tz.timestamp()

    def create_value(self, at_time: int | None = None) -> int:
        if at_time is None:
            at_time = int(self.get_date_timestamp("timestamp"))
        return at_time // self.expire_time

    def generate_api_key(self) -> str:
        timestamp = self.create_value()
        suffix = self.generate_suffix(timestamp)
        prefix = self.generate_prefix(timestamp)
        return f"{suffix}_{timestamp}_{prefix}"

    def generate_suffix(self, timestamp: int | None = None) -> str:
        timestamp = timestamp if timestamp is not None else self.create_value()
        suffix_num = math.sqrt(math.log10(timestamp)) or math.sqrt(math.log10(timestamp + 1))
        char_suffix = chr(int(suffix_num * 100) % 26 + 65)
        return char_suffix

    def generate_prefix(self, timestamp: int | None = None) -> str:
        timestamp = timestamp if timestamp is not None else self.create_value()
        prefix_num = math.pow(math.log1p(timestamp), 3) or math.pow(math.log1p(timestamp + 1), 3)
        char_prefix = chr(int(prefix_num * 100) % 26 + 65)
        return char_prefix


api_key_generator_instance = api_key_generator()
