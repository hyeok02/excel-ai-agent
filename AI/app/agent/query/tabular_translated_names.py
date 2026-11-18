"""Which question words name a planned filter value, asked only among the column's own values."""
import asyncio
import re

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
    # "유병률" picks Attack Prevalence when it is listed first and Current Prevalence when that
    # is: a word fitting more than one value names neither. Asked again in reverse order, a
    # word naming one value still picks it.
    reverse = list(reversed(chunks[home]))
    if len(reverse) > 1:
        # A reading can also depend on order the other way: "목조 건물" is left unmatched with Frame
        # listed first and read as Frame with it last. When no word picks the value, a word
        # matching nothing in one order and the planned value in the other names it.
        asked = named or [word for word, result in zip(words, first) if result.status == "unmatched"]
        again = await asyncio.gather(*(resolver.resolve(word, field, reverse) for word in asked))
        named = [word for word, result in zip(asked, again) if _picks(result, reverse, planned)]
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


async def column_words(resolver, words, table, plan):
    """([(word, label)] naming columns the plan computes, conflict) asked among all column labels.

    Labels are the headers and the parent headers above them ("가정용" names Residential, the
    parent of "August 2026"). conflict: a word names only columns the plan never reads ("영국"
    is United Kingdom, the plan reads England); such a plan answers some other question.
    """
    labels = list(dict.fromkeys([column.header for column in table.columns]
                                + [text for column in table.columns for _, text in column.header_path]))
    under = lambda label: {column.id for column in table.columns
                           if column.header == label or any(text == label for _, text in column.header_path)}
    read = {*plan.column_ids, *plan.group_by, *plan.identity_column_ids, *(item.column_id for item in plan.filters),
            *([plan.order_by] if plan.order_by else [])}
    results = await asyncio.gather(*(resolver.resolve(word, "column name", labels) for word in words))
    named = [(word, labels[result.candidate_id]) for word, result in zip(words, results)
             if result.status == "resolved" and type(result.candidate_id) is int
             and 0 <= result.candidate_id < len(labels)]
    named = [(word, label) for word, label in named if not any(word != other and other in word for other, _ in named)]
    # "계약" naming Policy, whose value is unique on every row, names what each row is: the thing counted.
    rows = lambda label: all(all(isinstance(row.values.get(column), str) for row in table.rows)
                             and len({row.values.get(column) for row in table.rows}) == len(table.rows) for column in under(label))
    conflict = any(not under(label) & read and not rows(label) for _, label in named)
    # A parent over several columns is stated as the one column the plan computes under it.
    computed = lambda label: [column for column in table.columns if column.id in under(label) & set(plan.column_ids)]
    return [(word, computed(label)[0].display_header if len(computed(label)) == 1 else label)
            for word, label in named if computed(label)], conflict


_TOTAL = re.compile(r"(?:all|total|grand\s+total|overall)(?:\s+\S.*)?|전체(?:\s*\S.*)?|합계|총계|총합", re.I)


async def names_no_member(resolver, words, field, values, planned):
    """The planned value is the column's total row and no word names any member of the column.

    "잉글랜드 인구" names no Groups/Codes member (Males, Females, an age band), so the plan's
    All Persons row is the population asked about. The same readings are asked as for the
    words themselves, so a cached reading costs no further call.
    """
    if not _TOTAL.fullmatch(str(planned).strip()) or len(values) > CHUNK:
        return False
    results = await asyncio.gather(*(resolver.resolve(word, field, values) for word in words))
    return all(result.status == "unmatched" for result in results)


_YES = {"y", "yes", "true", "o", "예", "있음"}
_NO = {"n", "no", "false", "x", "아니오", "없음"}
_NEGATED = re.compile(r"미가입|미보유|없는|없음|아닌|않은|안\s*한|제외|\bnot\b|\bno\b|\bwithout\b", re.I)


async def affirmed_columns(resolver, words, table, conditions, question):
    """{condition index: word} for yes/no columns the question names without negating them.

    "지진 보험 가입 계약 수" names Earthquake, a column holding only Y and N, and the plan keeps
    Y: naming the column affirms it. Any negation ("미가입", "없는") leaves it unread.
    """
    columns = {column.id: column for column in table.columns}
    binary = {index: condition for index, condition in enumerate(conditions)
              if normalize(condition.value) in _YES and {normalize(row.values.get(condition.column_id))
                                                         for row in table.rows} - {"", "none"} <= _YES | _NO}
    if not binary or _NEGATED.search(question):
        return {}
    headers = [columns[condition.column_id].header for condition in binary.values()]
    results = await asyncio.gather(*(resolver.resolve(word, "column name", headers) for word in words))
    named = {headers[result.candidate_id]: word for word, result in reversed(list(zip(words, results)))
             if result.status == "resolved" and type(result.candidate_id) is int and 0 <= result.candidate_id < len(headers)}
    return {index: named[columns[condition.column_id].header] for index, condition in binary.items()
            if columns[condition.column_id].header in named}
