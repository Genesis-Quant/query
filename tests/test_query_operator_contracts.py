"""Condition operators reject numeric input before a workflow is created."""

import pytest
from pydantic import ValidationError

from query.apps.query.schema import FactorQuery

CONDITION_OPERATORS = [
    "bars_since", "consecutive_count", "rolling_true_count", "rolling_all", "rolling_any",
]


def query_for(operation, operand):
    return {
        "start_date": "2025-01-01", "end_date": "2025-01-10", "codes": [],
        "derivatives": {
            "counted": {
                "type": "TS", "op": f"unary.{operation}", "fields": {"col": operand},
                "params": {"window": 5} if operation.startswith("rolling_") else {},
            },
        },
    }


@pytest.mark.parametrize("operation", CONDITION_OPERATORS)
@pytest.mark.parametrize("operand", ["close", 11.43, 1])
def test_condition_operators_reject_price_fields_and_numeric_literals(operation, operand):
    with pytest.raises(ValidationError):
        FactorQuery.model_validate(query_for(operation, operand))


@pytest.mark.parametrize("operation", CONDITION_OPERATORS)
@pytest.mark.parametrize("operand", [True, False, {
    "type": "DIRECT", "op": "binary.gt", "fields": {"left": "close", "right": 0},
}])
def test_condition_operators_accept_boolean_inputs(operation, operand):
    FactorQuery.model_validate(query_for(operation, operand))


@pytest.mark.parametrize("period", [0, 1, 2, 14])
@pytest.mark.parametrize("operation", ["atr", "natr"])
def test_atr_period_matches_runtime_minimum(period, operation):
    query = {
        "start_date": "2025-01-01", "end_date": "2025-01-10", "codes": [],
        "derivatives": {"atr": {
            "type": "TS", "op": f"talib.{operation}",
            "fields": {"high": "high", "low": "low", "close": "close"},
            "params": {"time_period": period},
        }},
    }
    if period < 2:
        with pytest.raises(ValidationError):
            FactorQuery.model_validate(query)
    else:
        FactorQuery.model_validate(query)
