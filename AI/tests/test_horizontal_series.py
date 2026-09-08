from app.services.insights.facts.horizontal_series import extract_horizontal_series


def cell(address, value, number_format="General"):
    return {
        "address": address,
        "value": value,
        "formula": None,
        "cached_value": None,
        "number_format": number_format,
    }


def region(*rows):
    return {"analysis_rows": list(rows), "preview_rows": list(rows)}


def test_repeated_and_reversing_dates_split_reporting_bases():
    data = region(
        [
            cell("D1", "2024-01-31T00:00:00"),
            cell("E1", "2025-01-31T00:00:00"),
            cell("F1", "2026-01-31T00:00:00"),
            cell("G1", "2026-01-31T00:00:00"),
            cell("H1", "2025-01-31T00:00:00"),
            cell("I1", "2026-01-31T00:00:00"),
        ],
        [cell("B3", "Net Income"), *[
            cell(f"{column}3", value, "0.0\\%")
            for column, value in zip("DEFGHI", (32.8, 25.3, 12.6, 12.6, -4.3, -19.3))
        ]],
    )

    series = extract_horizontal_series([data])

    assert [[point["value_cell"] for point in item["points"]] for item in series] == [
        ["D3", "F3"],
        ["H3", "I3"],
    ]


def test_actual_and_estimate_axes_remain_separate_across_blank_columns():
    data = region(
        [cell("E1", "Actuals"), cell("N1", "Estimates")],
        [
            cell("E2", "2021-12-31T00:00:00"),
            cell("F2", "2022-12-31T00:00:00"),
            cell("G2", "2023-12-31T00:00:00"),
            cell("H2", "2024-12-31T00:00:00"),
            cell("I2", "2025-12-31T00:00:00"),
            cell("J2", "2025-12-31T00:00:00"),
            cell("N2", "2026-12-31T00:00:00"),
            cell("O2", "2027-12-31T00:00:00"),
            cell("P2", "2028-12-31T00:00:00"),
        ],
        [cell("B4", "Total Revenue"), *[
            cell(f"{column}4", value)
            for column, value in zip("EFGHIJ", (10, 11, 12, 13, 14, 14))
        ], cell("N4", 15), cell("O4", 16), cell("P4", 17)],
    )

    series = extract_horizontal_series([data])

    assert [item["basis"] for item in series] == ["Actuals", "Estimates"]
    assert [item["points"][-1]["period_cell"] for item in series] == ["I2", "P2"]


def test_heading_between_axis_and_body_becomes_series_scope():
    data = region(
        [cell("D8", "2024-01-31T00:00:00"), cell("E8", "2025-01-31T00:00:00")],
        [cell("B9", "1 Year Growth (%)")],
        [cell("B10", "Revenue"), cell("D10", 6.1), cell("E10", 4.7)],
    )

    [series] = extract_horizontal_series([data])

    assert series["scope"] == "1 Year Growth (%)"
    assert series["scope_cell"] == "B9"
    assert series["label_cell"] == "B10"
