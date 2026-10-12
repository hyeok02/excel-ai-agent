"""수식의 대괄호가 다른 파일을 가리키는지, 표의 열 이름인지 가려낸다."""
import re

# Table1[Amount], Sales_T[[#This Row],[Qty]] 처럼 표 이름이 앞에 붙은 대괄호.
STRUCTURED_REFERENCE = re.compile(
    r"[A-Za-z_\uac00-\ud7a3][A-Za-z0-9_.\uac00-\ud7a3]*"
    r"\[(?:[^\[\]]|\[[^\[\]]*\])*\]"
)


def references_other_file(text: object) -> bool:
    """
    표 구조적 참조를 외부 파일 참조로 세면 평범한 표에 경고가 행마다 뜬다.

    진짜 외부 참조는 [1]Sheet1!A1 이나 'C:\\폴더\\[Book.xlsx]Sheet1'!A1 처럼
    대괄호 앞에 표 이름이 없다. 표 이름이 붙은 대괄호를 먼저 지우고 남는지 본다.
    """
    return "[" in STRUCTURED_REFERENCE.sub("", str(text or ""))
