"""Which question words name a planned filter value, asked only among the column's own values."""
import asyncio

from app.agent.query.tabular_request_predicates import normalize

CHUNK = 250
MAX_VALUES = 1_000


def _picks(result, chunk, planned):
    return (result.status == "resolved" and type(result.candidate_id) is int
            and 0 <= result.candidate_id < len(chunk) and normalize(chunk[result.candidate_id]) == normalize(planned))


async def words_naming(resolver, words, field, values, planned):
    """Words that name exactly the planned value, or None when the column is too long to ask.

    A column longer than one request is asked in parts. A word counts only when it picks
    the planned value in the part holding it and clearly matches nothing in every other part.
    """
    if len(values) > MAX_VALUES:
        return None
    chunks = [values[start:start + CHUNK] for start in range(0, len(values), CHUNK)]
    home = next(index for index, chunk in enumerate(chunks)
                if any(normalize(value) == normalize(planned) for value in chunk))
    first = await asyncio.gather(*(resolver.resolve(word, field, chunks[home]) for word in words))
    named = [word for word, result in zip(words, first) if _picks(result, chunks[home], planned)]
    others = [chunk for index, chunk in enumerate(chunks) if index != home]
    if not named or not others:
        return named
    pairs = [(word, chunk) for word in named for chunk in others]
    checks = await asyncio.gather(*(resolver.resolve(word, field, chunk) for word, chunk in pairs))
    elsewhere = {word for (word, _), result in zip(pairs, checks) if result.status != "unmatched"}
    return [word for word in named if word not in elsewhere]


def contains_as_equals(plan, table):
    """"contains Cookies" picks exactly the rows "= Cookies" does when Cookies is the only value holding it."""
    filters = []
    for item in plan.filters:
        if item.operator == "contains" and isinstance(item.value, str) and item.value.strip():
            holding = {value for row in table.rows if isinstance(value := row.values.get(item.column_id), str)
                       and normalize(item.value) in normalize(value)}
            if len(holding) == 1 and normalize(next(iter(holding))) == normalize(item.value):
                item = item.model_copy(update={"operator": "equals", "value": next(iter(holding))})
        filters.append(item)
    return plan.model_copy(update={"filters": filters})


def assigned_words(found):
    """One distinct word per condition, or None.

    "쿠키" and "쿠키 판매수량" are one mention, so the shortest wording counts. A word only one
    condition can take is taken there first: "초코칩" names Product = Chocolate Chip, so it is
    not also Category's word beside "쿠키". Anything still shared or missing reads nothing.
    """
    if any(named is None for named in found):
        return None
    options = [{word for word in named if not any(word != other and other in word for other in named)}
               for named in found]
    chosen = [None] * len(options)
    while forced := [index for index, words in enumerate(options) if chosen[index] is None and len(words) == 1]:
        index = forced[0]
        chosen[index] = word = next(iter(options[index]))
        for other in range(len(options)):
            if chosen[other] is None:
                options[other].discard(word)
    return chosen if None not in chosen and len(set(chosen)) == len(chosen) else None


async def metric_word(resolver, words, table, plan):
    """(word, header) when exactly one word names a column the plan computes, asked among all headers."""
    headers = [column.header for column in table.columns]
    computed = {column.header for column in table.columns if column.id in plan.column_ids}
    results = await asyncio.gather(*(resolver.resolve(word, "column name", headers) for word in words))
    named = [(word, headers[result.candidate_id]) for word, result in zip(words, results)
             if result.status == "resolved" and type(result.candidate_id) is int
             and 0 <= result.candidate_id < len(headers) and headers[result.candidate_id] in computed]
    named = [(word, header) for word, header in named if not any(word != other and other in word for other, _ in named)]
    return named[0] if len(named) == 1 else None
