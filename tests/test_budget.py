import pytest

from llm_stego_public_key.errors import BudgetError
from llm_stego_public_key.evaluation.budget import BudgetLedger, TokenMeter


def test_restart_charges_entire_abandoned_job(tmp_path):
    path = tmp_path / "budget.jsonl"
    limits = {"seconds": 10, "tokens": 20, "cases": 2}
    ledger = BudgetLedger(path, limits)
    ledger.reserve(5, 10)
    ledger.close()  # Simulate controller crash: no settlement.
    ledger = BudgetLedger(path, limits)
    assert ledger.usage() == {"seconds": 5, "tokens": 10, "cases": 1}
    aid = ledger.reserve(5, 10)
    with pytest.raises(BudgetError):
        ledger.reserve(0.01, 0, 0)
    ledger.settle(aid, 2, 3)
    assert ledger.usage() == {"seconds": 7, "tokens": 13, "cases": 2}
    with pytest.raises(BudgetError):
        ledger.reserve(0, 0, 1)
    with pytest.raises(BudgetError):
        ledger.settle(aid, 2, 3)
    ledger.close()


@pytest.mark.parametrize("reservation", [(11, 0, 0), (0, 21, 0), (0, 0, 3)])
def test_each_ceiling_is_enforced(tmp_path, reservation):
    ledger = BudgetLedger(tmp_path / "b.jsonl", {"seconds": 10, "tokens": 20, "cases": 2})
    with pytest.raises(BudgetError):
        ledger.reserve(*reservation)
    ledger.close()


def test_no_concurrent_controller_and_corruption_fail_closed(tmp_path):
    path = tmp_path / "b.jsonl"
    a = BudgetLedger(path)
    with pytest.raises(BudgetError):
        BudgetLedger(path)
    path.write_text('{"partial":')
    with pytest.raises(BudgetError):
        a.reserve(1, 1)
    a.close()


def test_token_meter_charges_before_work_and_exact_limit():
    meter = TokenMeter(3)
    meter.phase = "reconstruction"
    meter.charge(3)
    with pytest.raises(BudgetError):
        meter.charge(1)
    assert meter.tokens == 3
    assert meter.by_phase == {"reconstruction": 3}
