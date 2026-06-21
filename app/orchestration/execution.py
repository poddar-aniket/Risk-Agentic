"""
Simulated execution layer (Stage 5, stretch goal).

When a human approves a Decision on the dashboard, this module writes mock
updates to the suppliers/inventory tables to simulate the action actually
being carried out. This is purely a demo artifact -- there is no real ERP,
warehouse, or supplier integration behind it.

DELIBERATE SCOPE LIMIT: DecisionProposal.magnitude is free text (e.g. "500
units reorder", "2 week hold"), not a structured number. Parsing that with
regex to decide a numeric stock_level delta would be exactly the kind of
fragile, hardcoded logic this project has avoided everywhere else (see the
ingestion session's rejected local keyword pre-filter for the same reasoning).
So this module only performs the subset of action_types that map
unambiguously from action_type alone, with no parsing of magnitude:

    PLACE_REORDER, EXPEDITE_SHIPMENT  -> mark_reorder_placed on the resolved
                                          inventory row
    HOLD_SUPPLIER, FIND_ALTERNATE_SUPPLIER -> set_status(supplier, "on_hold")
    INCREASE_SAFETY_STOCK, MONITOR_ONLY    -> no table mutation (logged only)

Numeric stock_level/reorder_threshold simulation is a known, deliberate gap --
revisit only if DecisionProposal is ever extended with a structured quantity
field (e.g. `quantity_units: Optional[int]`) so the Decision Agent's LLM call
itself produces the number, rather than this layer guessing at one.
"""
import logging

from sqlalchemy.orm import Session

from app.agents.schemas import ActionType
from app.db.inventory_repository import InventoryRepository
from app.db.supplier_repository import SupplierRepository
from app.models.decision import Decision

logger = logging.getLogger(__name__)

# action_types that resolve to a supplier and flip its status to on_hold.
_HOLD_SUPPLIER_ACTIONS = {ActionType.HOLD_SUPPLIER, ActionType.FIND_ALTERNATE_SUPPLIER}

# action_types that resolve to a specific inventory row and mark a reorder placed.
_MARK_REORDER_ACTIONS = {ActionType.PLACE_REORDER, ActionType.EXPEDITE_SHIPMENT}

# action_types with no unambiguous table mutation -- see module docstring.
_NO_OP_ACTIONS = {ActionType.INCREASE_SAFETY_STOCK, ActionType.MONITOR_ONLY}


def _resolve_supplier(db: Session, decision: Decision):
    """Look up the supplier a Decision targets by name. Returns the first
    match, logging a warning if the name is ambiguous (matches more than
    one supplier) or matches none -- either case means simulated execution
    can't proceed for this decision, but should not raise: the approval
    itself already succeeded and should not be rolled back over a demo-layer
    lookup miss."""
    matches = SupplierRepository(db).get_by_name(decision.target_supplier_name)
    if not matches:
        logger.warning(
            "Simulated execution: no supplier matching '%s' for decision %s -- skipping",
            decision.target_supplier_name,
            decision.id,
        )
        return None
    if len(matches) > 1:
        logger.warning(
            "Simulated execution: '%s' matched %d suppliers for decision %s, using first match (id=%s)",
            decision.target_supplier_name,
            len(matches),
            decision.id,
            matches[0].id,
        )
    return matches[0]


def execute_approved_decision(decision: Decision, db: Session) -> str:
    """Apply the Stage 5 simulated table mutation for a just-approved Decision.

    Returns a short human-readable string describing what happened, for
    logging/response purposes. Never raises -- a simulated-execution lookup
    miss is logged and skipped, not surfaced as an approval failure, since
    the approve endpoint's primary contract (flip Decision.status) has
    already succeeded by the time this runs.
    """
    try:
        action_type = ActionType(decision.action_type)
    except ValueError:
        logger.warning(
            "Simulated execution: unrecognized action_type '%s' on decision %s -- skipping",
            decision.action_type,
            decision.id,
        )
        return "skipped: unrecognized action_type"

    if action_type in _NO_OP_ACTIONS:
        logger.info(
            "Simulated execution: action_type %s has no table mutation by design (decision %s)",
            action_type.value,
            decision.id,
        )
        return f"no-op (by design): {action_type.value}"

    supplier = _resolve_supplier(db, decision)
    if supplier is None:
        return "skipped: supplier not found"

    if action_type in _HOLD_SUPPLIER_ACTIONS:
        SupplierRepository(db).set_status(supplier.id, "on_hold")
        logger.info(
            "Simulated execution: supplier %s (id=%s) set to on_hold (decision %s, action %s)",
            supplier.name,
            supplier.id,
            decision.id,
            action_type.value,
        )
        return f"supplier '{supplier.name}' set to on_hold"

    if action_type in _MARK_REORDER_ACTIONS:
        inventory_repo = InventoryRepository(db)
        inventory_row = inventory_repo.get_by_supplier_and_product(
            supplier.id, decision.target_product
        )
        if inventory_row is None:
            logger.warning(
                "Simulated execution: no inventory row for supplier '%s' / product '%s' "
                "(decision %s) -- skipping",
                supplier.name,
                decision.target_product,
                decision.id,
            )
            return "skipped: inventory row not found"

        inventory_repo.mark_reorder_placed(inventory_row.id)
        logger.info(
            "Simulated execution: reorder marked placed for %s / %s (decision %s, action %s)",
            supplier.name,
            inventory_row.product,
            decision.id,
            action_type.value,
        )
        return f"reorder marked placed: '{supplier.name}' / '{inventory_row.product}'"

    # Should be unreachable given ActionType has exactly six members, all
    # covered by the three sets above -- but fail loud-but-soft rather than
    # silently doing nothing if a seventh action_type is ever added without
    # updating this module.
    logger.warning(
        "Simulated execution: action_type %s not mapped to any handler (decision %s)",
        action_type.value,
        decision.id,
    )
    return f"skipped: action_type {action_type.value} not mapped"
