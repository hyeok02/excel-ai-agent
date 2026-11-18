"""What is still tried when every stage has answered nothing.

Each reads the source directly and answers only a question shaped for it; anything else stays
unanswered as before, so no question that was answered reaches here or changes.
"""
from app.agent.query.column_change_counts import column_change_count_answer
from app.agent.query.series_value_answers import series_value_answer


def final_answer(question, summary, index):
    # "2025년 총발전량": a period's cell in a sheet read section by section.
    # "작년보다 오른 주는 몇 개": rows whose newer value is above their older one.
    return series_value_answer(question, summary, index) or column_change_count_answer(question, summary, index)
