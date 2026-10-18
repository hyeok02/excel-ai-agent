"""Search truncation remains separate from bounded, explicit source coverage."""


def search_scope_truncated(execution) -> bool:
    return any(
        bool(step.result.data.get("index_truncated"))
        for step in execution.steps
        if step.result and isinstance(step.result.data, dict)
    )
