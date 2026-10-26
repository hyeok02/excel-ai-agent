"""Keep natural-language target labels and each replacement operation separate."""
import re

from app.agent.writeback.target_syntax import sheet_mentions

SEPARATOR = re.compile(
    r"(?:으로|로)\s*(?:수정(?:해줘)?|변경(?:해줘)?|바꿔(?:줘)?)?\s*[,;\n]"
    r"|(?:수정해줘|변경해줘|바꿔줘|비워줘|지워줘)\s*[,;\n]", re.I,
)
ASSIGNMENT = re.compile(r"(?:을|를|은|는)\s+|\b(?:to|as)\s+", re.I)


def natural_operations(instruction, sheets):
    start, inherited, operations = 0, None, []
    for end in [*(match.end() for match in SEPARATOR.finditer(instruction)), len(instruction)]:
        clause = instruction[start:end].strip(" ,;\n")
        start = end
        if not clause:
            continue
        mentioned = sheet_mentions(clause, sheets)
        if mentioned:
            inherited = mentioned[-1][2]
        elif inherited:
            clause = f"'{inherited.replace(chr(39), chr(39) * 2)}' {clause}"
        operations.append(clause)
    return operations


def value_instruction(instruction):
    """Source labels cannot be authorized as replacement text/numbers."""
    matches = list(ASSIGNMENT.finditer(instruction))
    return instruction[matches[-1].end():] if matches else instruction
