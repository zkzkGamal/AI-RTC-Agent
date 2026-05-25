import datetime
import math
import time
from zoneinfo import ZoneInfo


class api_key_generator:
    def __init__(self, expire_time: int = 60):
        self.secret_key = None
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
            if self.time_zone:
                at_time = int(self.get_date_timestamp("timestamp"))
            else:
                at_time = int(time.time())
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

    def validate_api_key(self, api_key: str, grace_windows: int = 1) -> bool:
        try:
            suffix, timestamp_str, prefix = api_key.split("_")
            timestamp = int(timestamp_str)
            current_timestamp = self.create_value()

            if timestamp > current_timestamp:
                return False

            if current_timestamp - timestamp > grace_windows:
                return False

            expected_suffix = self.generate_suffix(timestamp)
            expected_prefix = self.generate_prefix(timestamp)
            return suffix == expected_suffix and prefix == expected_prefix
        except Exception:
            return False
