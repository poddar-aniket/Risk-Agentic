"""
Supplier DB model — represents a vendor in the mock supplier dataset.
products_supplied stays as CSV for simplicity in a 4-5 day build.
status drives the simulated execution layer on Day 5 (approve -> on_hold).
"""
from sqlalchemy import Column, Integer, String

from app.db.session import Base


class Supplier(Base):
    __tablename__ = "suppliers"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    region = Column(String, nullable=False)       # e.g. "Tamil Nadu", "Maharashtra"
    products_supplied = Column(String)            # CSV: "rice,wheat,sugar"
    contact_email = Column(String, nullable=True)
    status = Column(String, default="active")     # "active" | "on_hold"
