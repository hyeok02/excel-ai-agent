"""Say which sheet a distribution came from, and when a sibling column exists."""
def scope_prefix(sheet: str, qualify: bool) -> str:
    """
    여러 시트짜리 파일에서 한 시트의 한 열만 센 결과는 그 사실을 달고 나가야 한다.

    근거 셀에는 시트 이름이 적히지만 문장에는 없어서, 파일 전체를 센 것처럼 읽혔다.
    """
    return f"‘{sheet}’ 시트에서 " if qualify and sheet else ""
