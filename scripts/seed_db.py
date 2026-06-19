"""
Seed script — populates the SQLite DB with mock supplier and inventory data.
Run once before the first pipeline run:

    python -m scripts.seed_db

This gives the Risk Analysis Agent real numbers to reason over (stock levels,
daily consumption, lead times) rather than hitting an empty DB.
"""
from app.db.session import Base, SessionLocal, engine
from app.models.inventory import Inventory
from app.models.supplier import Supplier

SUPPLIERS = [
    {"name": "Ramesh Agro Suppliers", "region": "Tamil Nadu", "products_supplied": "rice,wheat", "status": "active"},
    {"name": "Maharashtra Grain Co.", "region": "Maharashtra", "products_supplied": "wheat,sugar", "status": "active"},
    {"name": "Kerala Spice Exports", "region": "Kerala", "products_supplied": "pepper,cardamom,turmeric", "status": "active"},
    {"name": "Punjab Farm Fresh", "region": "Punjab", "products_supplied": "wheat,rice,mustard", "status": "active"},
    {"name": "Gujarat Textile Mills", "region": "Gujarat", "products_supplied": "cotton,yarn", "status": "active"},
]

INVENTORY = [
    # supplier_index (0-based), product, stock_level, avg_daily, lead_time_days, threshold
    (0, "rice",       1200, 80,  14, 560),
    (0, "wheat",       800, 50,  14, 350),
    (1, "wheat",      1500, 90,  10, 450),
    (1, "sugar",       600, 40,  21, 280),
    (2, "pepper",      300, 15,  30, 150),
    (2, "cardamom",    150,  8,  30,  80),
    (2, "turmeric",    400, 20,  21, 140),
    (3, "wheat",      2000, 120, 10, 600),
    (3, "rice",        900,  60, 14, 420),
    (4, "cotton",      500,  30, 45, 270),
    (4, "yarn",        350,  25, 30, 175),
]


def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.query(Supplier).count() > 0:
            print("DB already seeded — skipping.")
            return

        supplier_ids = []
        for s in SUPPLIERS:
            supplier = Supplier(**s)
            db.add(supplier)
            db.flush()
            supplier_ids.append(supplier.id)
            print(f"  Added supplier: {s['name']} (id={supplier.id})")

        for supplier_idx, product, stock, daily, lead, threshold in INVENTORY:
            inv = Inventory(
                supplier_id=supplier_ids[supplier_idx],
                product=product,
                stock_level=stock,
                avg_daily_consumption=daily,
                reorder_lead_time=lead,
                reorder_threshold=threshold,
                reorder_placed=False,
            )
            db.add(inv)

        db.commit()
        print(f"\nSeeded {len(SUPPLIERS)} suppliers and {len(INVENTORY)} inventory rows.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
