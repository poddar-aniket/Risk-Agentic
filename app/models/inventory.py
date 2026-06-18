from sqlalchemy import Boolean, Column, Float, ForeignKey, Integer, String

from app.db.session import Base


class Inventory(Base):
    __tablename__ = "inventory"

    id = Column(Integer, primary_key=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"))
    product = Column(String, nullable=False)
    stock_level = Column(Float, default=0)
    avg_daily_consumption = Column(Float, default=0)
    reorder_lead_time = Column(Integer, default=0)
    reorder_threshold = Column(Float, default=0)
    reorder_placed = Column(Boolean, default=False)
