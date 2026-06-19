"""
Seed script for mock supplier + inventory data (SQLite dev DB).

Mirrors the pattern of app/rag/seed.py: run once per fresh environment to
populate the suppliers and inventory tables that Risk Analysis Agent,
Supplier Agent, and Decision Agent all depend on.

Run from repo root:
    set PYTHONPATH=.
    python data/seed/seed_supply_data.py

Safe to re-run: checks for existing rows by supplier name before inserting,
so it won't create duplicates on a second run.
"""

from app.db.session import Base, SessionLocal, engine
from app.db.supplier_repository import SupplierRepository
from app.db.inventory_repository import InventoryRepository
from app.models.supplier import Supplier
from app.models.inventory import Inventory


# ---------------------------------------------------------------------------
# Mock data. Regions chosen to span common disruption zones (ports, industrial
# clusters) so Geo Agent's affected_regions output has real suppliers to match.
# Two inventory rows are deliberately seeded near/below reorder_threshold so
# Decision Agent has a concrete reorder scenario to reason about on first run.
# ---------------------------------------------------------------------------

SUPPLIERS = [
    {
        "name": "Chennai Textile Exports",
        "region": "Tamil Nadu",
        "products_supplied": "cotton,yarn,fabric",
        "contact_email": "ops@chennaitex.example.com",
        "status": "active",
    },
    {
        "name": "Mumbai Port Logistics Co",
        "region": "Maharashtra",
        "products_supplied": "rice,wheat,sugar",
        "contact_email": "supply@mumbailogi.example.com",
        "status": "active",
    },
    {
        "name": "Gujarat AgroSupply",
        "region": "Gujarat",
        "products_supplied": "cotton,groundnut,salt",
        "contact_email": "sales@gujaratagro.example.com",
        "status": "active",
    },
    {
        "name": "Kolkata Jute Mills",
        "region": "West Bengal",
        "products_supplied": "jute,tea,rice",
        "contact_email": "contact@kolkatajute.example.com",
        "status": "active",
    },
    {
        "name": "Bengaluru Electronics Components",
        "region": "Karnataka",
        "products_supplied": "semiconductors,circuit boards",
        "contact_email": "procurement@blrelec.example.com",
        "status": "active",
    },
    {
        "name": "Punjab Grain Traders",
        "region": "Punjab",
        "products_supplied": "wheat,rice,sugar",
        "contact_email": "info@punjabgrain.example.com",
        "status": "active",
    },
]

# Each entry: (supplier_name, product, stock_level, avg_daily_consumption,
#              reorder_lead_time, reorder_threshold, reorder_placed)
INVENTORY = [
    # Chennai Textile Exports — healthy stock
    ("Chennai Textile Exports", "cotton", 5000, 120, 7, 800, False),
    ("Chennai Textile Exports", "fabric", 3000, 90, 5, 600, False),

    # Mumbai Port Logistics — one item deliberately LOW (near threshold)
    ("Mumbai Port Logistics Co", "rice", 1200, 200, 10, 1000, False),  # ~6 days left, near threshold
    ("Mumbai Port Logistics Co", "wheat", 8000, 150, 7, 1000, False),

    # Gujarat AgroSupply — healthy
    ("Gujarat AgroSupply", "cotton", 4500, 100, 6, 700, False),
    ("Gujarat AgroSupply", "groundnut", 2200, 80, 5, 500, False),

    # Kolkata Jute Mills — one item BELOW threshold (already needs reorder)
    ("Kolkata Jute Mills", "jute", 300, 60, 12, 500, False),  # below threshold, 5 days left
    ("Kolkata Jute Mills", "tea", 6000, 110, 7, 800, False),

    # Bengaluru Electronics — low daily consumption, long lead time (high risk profile)
    ("Bengaluru Electronics Components", "semiconductors", 1500, 40, 21, 1200, False),

    # Punjab Grain Traders — healthy
    ("Punjab Grain Traders", "wheat", 9000, 180, 5, 1500, False),
    ("Punjab Grain Traders", "rice", 7000, 160, 5, 1200, False),
]


def seed_suppliers(db, supplier_repo: SupplierRepository) -> dict[str, int]:
    """Insert suppliers if not already present. Returns name -> id map."""
    name_to_id: dict[str, int] = {}

    for s in SUPPLIERS:
        existing = supplier_repo.get_by_name(s["name"])
        if existing:
            print(f"Skipping existing supplier: {s['name']}")
            name_to_id[s["name"]] = existing.id
            continue

        supplier = Supplier(
            name=s["name"],
            region=s["region"],
            products_supplied=s["products_supplied"],
            contact_email=s["contact_email"],
            status=s["status"],
        )
        created = supplier_repo.add(supplier)
        name_to_id[s["name"]] = created.id
        print(f"Inserted supplier: {s['name']} (id={created.id})")

    return name_to_id


def seed_inventory(db, inventory_repo: InventoryRepository, name_to_id: dict[str, int]) -> None:
    for (supplier_name, product, stock_level, avg_daily_consumption,
         reorder_lead_time, reorder_threshold, reorder_placed) in INVENTORY:

        supplier_id = name_to_id.get(supplier_name)
        if supplier_id is None:
            print(f"WARNING: no supplier id found for '{supplier_name}', skipping inventory row")
            continue

        # Duplicate guard: skip if this supplier+product pair already exists.
        existing_rows = inventory_repo.get_by_supplier(supplier_id)
        if any(row.product == product for row in existing_rows):
            print(f"Skipping existing inventory row: {supplier_name} / {product}")
            continue

        inv = Inventory(
            supplier_id=supplier_id,
            product=product,
            stock_level=stock_level,
            avg_daily_consumption=avg_daily_consumption,
            reorder_lead_time=reorder_lead_time,
            reorder_threshold=reorder_threshold,
            reorder_placed=reorder_placed,
        )
        created = inventory_repo.add(inv)
        print(f"Inserted inventory: {supplier_name} / {product} (id={created.id})")


def main():
    # Tables don't exist in the SQLite file yet — no migration tooling is set
    # up (migrations/ is empty per the project doc), so create_all() here is
    # the dev-environment substitute. Safe to call every run: it's a no-op
    # for tables that already exist.
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        supplier_repo = SupplierRepository(db)
        inventory_repo = InventoryRepository(db)

        name_to_id = seed_suppliers(db, supplier_repo)
        seed_inventory(db, inventory_repo, name_to_id)

        print("Seed complete.")
    finally:
        db.close()


if __name__ == "__main__":
    main()