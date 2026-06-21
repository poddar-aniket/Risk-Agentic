"""
Tests for app/orchestration/execution.py (Day 5 simulated execution layer).

SupplierRepository and InventoryRepository are mocked at the class level
(patched where execution.py imports them) rather than hit against a real
DB. This module's job is pure routing/orchestration logic -- action_type
-> which repo method gets called with what args -- so isolating it from
the real Supplier/Inventory models keeps these tests focused on that
logic and not on schema details owned by other files. `db` itself is a
throwaway MagicMock since the repo classes are fully replaced.

Decision rows are built directly via the real SQLAlchemy model
(app.models.decision.Decision) without a session -- transient ORM
instances work fine for plain attribute access, which is all
execution.py ever does with one.

Run from repo root:
    set PYTHONPATH=.
    python -m pytest tests/test_execution.py -v
"""
import logging
from unittest.mock import MagicMock

import pytest

from app.agents.schemas import ActionType
from app.models.decision import Decision
from app.orchestration import execution as execution_module
from app.orchestration.execution import execute_approved_decision


def _make_decision(action_type="place_reorder",
                    target_supplier_name="Mumbai Port Logistics Co",
                    target_product="rice", **overrides):
    defaults = dict(
        id=1,
        action_type=action_type,
        target_supplier_name=target_supplier_name,
        target_product=target_product,
        justification="test justification",
        magnitude="500 units reorder",
        estimated_resolution_days=10,
        previously_rejected_options_checked=True,
        confidence_score=8.5,
        supervisor_approved=True,
        status="approved",
    )
    defaults.update(overrides)
    return Decision(**defaults)


class FakeSupplier:
    def __init__(self, id=42, name="Mumbai Port Logistics Co"):
        self.id = id
        self.name = name


class FakeInventoryRow:
    def __init__(self, id=99, product="rice"):
        self.id = id
        self.product = product


@pytest.fixture
def supplier_repo_cls(monkeypatch):
    """Patches SupplierRepository in execution.py's namespace with a class
    mock. SupplierRepository(db) -> cls_mock.return_value, so tests
    configure behavior via supplier_repo_cls.return_value.<method>."""
    cls_mock = MagicMock()
    monkeypatch.setattr(execution_module, "SupplierRepository", cls_mock)
    return cls_mock


@pytest.fixture
def inventory_repo_cls(monkeypatch):
    cls_mock = MagicMock()
    monkeypatch.setattr(execution_module, "InventoryRepository", cls_mock)
    return cls_mock


@pytest.fixture
def db():
    # Never actually touched -- SupplierRepository/InventoryRepository are
    # fully mocked above, so this stands in for the Session argument only.
    return MagicMock()


class TestExecutionNoOpActions:
    @pytest.mark.parametrize("action_type", ["increase_safety_stock", "monitor_only"])
    def test_no_op_actions_return_message_and_make_no_repo_calls(
        self, action_type, supplier_repo_cls, inventory_repo_cls, db
    ):
        decision = _make_decision(action_type=action_type)
        result = execute_approved_decision(decision, db)

        assert result == f"no-op (by design): {action_type}"
        # No-op actions should never even construct a repository -- if
        # this starts failing, a future edit accidentally started doing
        # supplier/inventory lookups for actions documented as no-ops.
        supplier_repo_cls.assert_not_called()
        inventory_repo_cls.assert_not_called()


class TestExecutionUnrecognizedActionType:
    def test_unrecognized_action_type_skips_without_repo_calls(
        self, supplier_repo_cls, inventory_repo_cls, db, caplog
    ):
        decision = _make_decision(action_type="teleport_inventory")  # not a real ActionType value

        with caplog.at_level(logging.WARNING):
            result = execute_approved_decision(decision, db)

        assert result == "skipped: unrecognized action_type"
        supplier_repo_cls.assert_not_called()
        inventory_repo_cls.assert_not_called()
        assert "unrecognized action_type" in caplog.text.lower()


class TestExecutionSupplierNotFound:
    def test_no_match_returns_skip_message_and_logs_warning(
        self, supplier_repo_cls, inventory_repo_cls, db, caplog
    ):
        supplier_repo_cls.return_value.get_by_name.return_value = []
        decision = _make_decision(action_type="place_reorder")

        with caplog.at_level(logging.WARNING):
            result = execute_approved_decision(decision, db)

        assert result == "skipped: supplier not found"
        assert "no supplier matching" in caplog.text.lower()

    def test_no_match_never_reaches_inventory_lookup(
        self, supplier_repo_cls, inventory_repo_cls, db
    ):
        supplier_repo_cls.return_value.get_by_name.return_value = []
        decision = _make_decision(action_type="place_reorder")

        execute_approved_decision(decision, db)

        inventory_repo_cls.return_value.get_by_supplier_and_product.assert_not_called()


class TestExecutionAmbiguousSupplierMatch:
    def test_ambiguous_match_uses_first_result_and_logs_warning(
        self, supplier_repo_cls, inventory_repo_cls, db, caplog
    ):
        first = FakeSupplier(id=10, name="Mumbai Port Logistics Co")
        second = FakeSupplier(id=11, name="Mumbai Port Logistics Co (Annex)")
        supplier_repo_cls.return_value.get_by_name.return_value = [first, second]
        decision = _make_decision(action_type="hold_supplier")

        with caplog.at_level(logging.WARNING):
            result = execute_approved_decision(decision, db)

        assert result == f"supplier '{first.name}' set to on_hold"
        supplier_repo_cls.return_value.set_status.assert_called_once_with(first.id, "on_hold")
        assert "matched 2 suppliers" in caplog.text


class TestExecutionHoldSupplierActions:
    @pytest.mark.parametrize("action_type", ["hold_supplier", "find_alternate_supplier"])
    def test_hold_actions_set_status_on_hold(
        self, action_type, supplier_repo_cls, inventory_repo_cls, db
    ):
        supplier = FakeSupplier(id=8, name="Kolkata Jute Mills")
        supplier_repo_cls.return_value.get_by_name.return_value = [supplier]
        decision = _make_decision(action_type=action_type)

        result = execute_approved_decision(decision, db)

        supplier_repo_cls.return_value.set_status.assert_called_once_with(supplier.id, "on_hold")
        assert result == f"supplier '{supplier.name}' set to on_hold"

    def test_hold_actions_never_touch_inventory_repo(
        self, supplier_repo_cls, inventory_repo_cls, db
    ):
        supplier = FakeSupplier()
        supplier_repo_cls.return_value.get_by_name.return_value = [supplier]
        decision = _make_decision(action_type="hold_supplier")

        execute_approved_decision(decision, db)

        inventory_repo_cls.assert_not_called()


class TestExecutionMarkReorderActions:
    @pytest.mark.parametrize("action_type", ["place_reorder", "expedite_shipment"])
    def test_mark_reorder_actions_resolve_and_mark_reorder(
        self, action_type, supplier_repo_cls, inventory_repo_cls, db
    ):
        supplier = FakeSupplier(id=5, name="Mumbai Port Logistics Co")
        supplier_repo_cls.return_value.get_by_name.return_value = [supplier]
        row = FakeInventoryRow(id=77, product="rice")
        inventory_repo_cls.return_value.get_by_supplier_and_product.return_value = row
        decision = _make_decision(action_type=action_type, target_product="rice")

        result = execute_approved_decision(decision, db)

        inventory_repo_cls.return_value.get_by_supplier_and_product.assert_called_once_with(
            supplier.id, "rice"
        )
        inventory_repo_cls.return_value.mark_reorder_placed.assert_called_once_with(row.id)
        assert result == f"reorder marked placed: '{supplier.name}' / '{row.product}'"

    def test_inventory_row_not_found_returns_skip_and_does_not_mark(
        self, supplier_repo_cls, inventory_repo_cls, db, caplog
    ):
        supplier = FakeSupplier(id=5, name="Mumbai Port Logistics Co")
        supplier_repo_cls.return_value.get_by_name.return_value = [supplier]
        inventory_repo_cls.return_value.get_by_supplier_and_product.return_value = None
        decision = _make_decision(action_type="place_reorder", target_product="unobtainium")

        with caplog.at_level(logging.WARNING):
            result = execute_approved_decision(decision, db)

        assert result == "skipped: inventory row not found"
        inventory_repo_cls.return_value.mark_reorder_placed.assert_not_called()
        assert "no inventory row" in caplog.text.lower()


class TestExecutionActionTypeCoverage:
    def test_every_action_type_is_mapped_to_exactly_one_handler_set(self):
        """Directly tests the maintenance hazard execution.py's own
        comment warns about: 'fail loud-but-soft rather than silently
        doing nothing if a seventh action_type is ever added without
        updating this module.' If ActionType ever gains a 7th member
        without updating _HOLD_SUPPLIER_ACTIONS / _MARK_REORDER_ACTIONS /
        _NO_OP_ACTIONS, this fails immediately instead of someone noticing
        a real approved decision silently doing nothing in a demo."""
        sets = [
            execution_module._HOLD_SUPPLIER_ACTIONS,
            execution_module._MARK_REORDER_ACTIONS,
            execution_module._NO_OP_ACTIONS,
        ]
        all_mapped = set()
        for s in sets:
            all_mapped |= s

        assert all_mapped == set(ActionType)

        for i in range(len(sets)):
            for j in range(i + 1, len(sets)):
                assert sets[i].isdisjoint(sets[j]), (
                    "An action_type appears in more than one handler set"
                )


class TestExecutionNeverRaisesClaimVsActualBehavior:
    def test_unexpected_repo_exception_is_caught_and_skipped(
        self, supplier_repo_cls, inventory_repo_cls, db, caplog
    ):
        """Regression guard for the fix that tightened execute_approved_
        decision()'s 'Never raises' guarantee. The original version only
        guarded the three documented lookup-miss paths; an unexpected
        exception from the repository layer (e.g. a real DB error, not a
        'supplier not found' miss) used to propagate straight past this
        function despite the unqualified docstring claim. Now it's caught
        by an outer guard around _execute_action() and turned into a skip
        message instead, matching what the docstring actually promises."""
        supplier_repo_cls.return_value.get_by_name.side_effect = RuntimeError("db connection lost")
        decision = _make_decision(action_type="place_reorder")

        with caplog.at_level(logging.WARNING):
            result = execute_approved_decision(decision, db)

        assert result == "skipped: unexpected error during simulated execution"
        assert "unexpected error executing decision" in caplog.text.lower()