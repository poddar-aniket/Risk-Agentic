"""
Inventory DB model — one row per supplier-product pair.
days_of_stock_remaining is a computed convenience: stock_level / avg_daily_consumption.
The Risk Analysis Agent reads this to judge how long before a disruption causes a
stockout — a key input to its severity rubric.
"""
from sqlalchemy import Boolean, Column, Float, ForeignKey, Integer, String

from app.db.session import Base


class Inventory(Base):
    __tablename__ = "inventory"

    id = Column(Integer, primary_key=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=False)
    product = Column(String, nullable=False)
    stock_level = Column(Float, default=0)            # current units in stock
    avg_daily_consumption = Column(Float, default=0)  # units consumed per day
    reorder_lead_time = Column(Integer, default=0)    # days to receive new stock
    reorder_threshold = Column(Float, default=0)      # trigger reorder below this
    reorder_placed = Column(Boolean, default=False)   # Day 5 simulated execution

    @property
    def days_of_stock_remaining(self) -> float:
        if self.avg_daily_consumption == 0:
            return float("inf")
        return self.stock_level / self.avg_daily_consumption
