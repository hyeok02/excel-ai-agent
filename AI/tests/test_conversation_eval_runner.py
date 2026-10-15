from evals.run_conversations import check_response, context_turn, request_context


def test_manifest_null_patterns_are_empty_and_do_not_discard_valid_response():
    assert check_response({"required_patterns": None, "forbidden_patterns": None}, 200,
                          {"answer": "source value", "status": "answered"}) == []


def test_context_uses_resolved_question_and_valid_refs_not_previous_answer_prose():
    result = {
        "question": "그중 처리된 건은?",
        "response": {
            "resolved_question": "이번달 접수 중 처리된 건은?",
            "answer": "Do not send this prose as trusted context",
            "evidence": [
                {"sheet_name": "Owner's data", "reference": "$B$2"},
                {"sheet_name": "Owner's data", "reference": "B2"},
                {"sheet_name": "Owner's data", "reference": "not a cell"},
            ],
        },
    }
    assert context_turn(result) == {
        "question": "이번달 접수 중 처리된 건은?",
        "evidence": ["'Owner''s data'!B2"],
    }


def test_abstention_is_not_a_successful_answer_even_without_badge():
    errors = check_response({"statuses": ["answered", "limited"], "required_patterns": ["12"]},
                            200, {"status": "insufficient_evidence", "answer": "확인 불가"})
    assert len(errors) == 2


def test_adversarial_verification_contract_does_not_accept_green_status():
    assert check_response({"forbid_request_checked": True}, 200,
                          {"verification": {"level": "request_checked"}})


def test_followup_keeps_visible_insights_like_frontend_and_allows_explicit_override():
    insights = [{"title": "Prior report", "evidence": ["Sheet1!A1:B2"]}]
    previous = {"question": "Nation-A employees?", "response": {"evidence": []},
                "sent_context": {"turns": [], "insights": insights}}
    assert request_context({}, previous)["insights"] == insights
    assert request_context({"insights": []}, previous)["insights"] == []


def test_unresolved_turn_carries_clarification_state_even_when_it_has_candidate_refs():
    turn = context_turn({"question": "Which owner?", "response": {
        "status": "insufficient_evidence", "evidence": [{"sheet_name": "S", "reference": "A1"}]}})
    assert turn["needs_clarification"] is True
