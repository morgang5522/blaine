import datetime
import re
from typing import Optional
try:
    import zoneinfo
except ImportError:
    from backports import zoneinfo  # type: ignore

COMMON_TZ_ABBR = {
    "UTC": datetime.timezone.utc,
    "GMT": datetime.timezone.utc,
    "EST": datetime.timezone(datetime.timedelta(hours=-5)),
    "EDT": datetime.timezone(datetime.timedelta(hours=-4)),
    "CST": datetime.timezone(datetime.timedelta(hours=-6)),
    "CDT": datetime.timezone(datetime.timedelta(hours=-5)),
    "MST": datetime.timezone(datetime.timedelta(hours=-7)),
    "MDT": datetime.timezone(datetime.timedelta(hours=-6)),
    "PST": datetime.timezone(datetime.timedelta(hours=-8)),
    "PDT": datetime.timezone(datetime.timedelta(hours=-7)),
    "BST": datetime.timezone(datetime.timedelta(hours=1)),
    "CET": datetime.timezone(datetime.timedelta(hours=1)),
    "CEST": datetime.timezone(datetime.timedelta(hours=2)),
    "JST": datetime.timezone(datetime.timedelta(hours=9)),
    "AEST": datetime.timezone(datetime.timedelta(hours=10)),
    "AEDT": datetime.timezone(datetime.timedelta(hours=11)),
}

def parse_timezone_str(tz_str: str) -> Optional[tuple[datetime.tzinfo, str]]:
    if not tz_str:
        return None
    clean = tz_str.strip()
    
    # 1. Direct ZoneInfo check (IANA names like America/New_York)
    try:
        tz = zoneinfo.ZoneInfo(clean)
        return tz, clean
    except Exception:
        pass

    # 2. Check uppercase abbreviation
    upper_clean = clean.upper()
    if upper_clean in COMMON_TZ_ABBR:
        return COMMON_TZ_ABBR[upper_clean], upper_clean

    # 3. Numeric UTC offset (e.g. UTC-5, GMT+2, -05:00, +01:00)
    match = re.match(r'^(?:UTC|GMT)?\s*([+-])\s*(\d{1,2})(?::?(\d{2}))?$', upper_clean)
    if match:
        sign = -1 if match.group(1) == '-' else 1
        hours = int(match.group(2))
        minutes = int(match.group(3)) if match.group(3) else 0
        offset = datetime.timedelta(hours=sign * hours, minutes=sign * minutes)
        tz_obj = datetime.timezone(offset)
        disp_name = f"UTC{match.group(1)}{hours:02d}:{minutes:02d}"
        return tz_obj, disp_name

    return None
