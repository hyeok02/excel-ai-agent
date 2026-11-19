"""What is still tried when every stage has answered nothing.

Each reads the source directly and answers only a question shaped for it; anything else stays
unanswered as before, so no question that was answered reaches here or changes.
"""
from app.agent.query.column_change_counts import column_change_count_answer
from app.agent.query.member_column_changes import member_change_answer
from app.agent.query.member_share_answers import member_share_answer
from app.agent.query.period_average_answers import period_average_answer
from app.agent.query.series_period_answers import series_period_answer
from app.agent.query.series_value_answers import series_value_answer


def final_answer(question, summary, index):
    # "2025년 총발전량": a period's cell in a sheet read section by section.
    # "작년보다 오른 주는 몇 개": rows whose newer value is above their older one.
    # "2024년 평균 병상 점유율": the mean of that year's monthly values in one series.
    # "하와이 상업용 전기요금은 작년보다 얼마나 올랐어": one row's change between two dated columns.
    return (series_value_answer(question, summary, index) or column_change_count_answer(question, summary, index)
            or period_average_answer(question, summary, index) or member_change_answer(question, summary, index)
            or series_period_answer(question, summary, index)  # two years' change, or the highest year
            or member_share_answer(question, summary, index))  # "Bars가 전체 판매금액에서 차지하는 비중"
