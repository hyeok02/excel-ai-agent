"""One source cell written as the reader expects: years without separators, whole days without a clock."""
import re

from app.agent.query.excel_number_formats import display_value, parse_number_format


def _display_cell(value, number_format, header=""):
    if value in (None, ""):
        return "빈칸"
    if isinstance(value, int) and not isinstance(value, bool) and 1000 <= value <= 2999 and _YEAR.fullmatch(header.strip()):
        return str(value)  # a year is written 2020, not 2,020
    if isinstance(value, int) and not isinstance(value, bool) and number_format in ("General", "", None) \
            and _CODE.search(header.strip()):
        return str(value)  # a zip code or an ID is written 70119, not 70,119
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return display_value(value, parse_number_format(number_format))
    # A whole day read as a timestamp ("2022-06-03T00:00:00") is written as that day.
    return re.sub(r"^(\d{4}-\d{2}-\d{2})[T ]00:00:00$", r"\1", value.isoformat() if hasattr(value, "isoformat") else str(value))


_CODE = re.compile(r"\b(?:zip|postal|postcode|id|code)\b|우편번호|사번|학번|코드|번호", re.I)
_YEAR = re.compile(r"year|years|연도|년도|년|기준\s*연도", re.I)
