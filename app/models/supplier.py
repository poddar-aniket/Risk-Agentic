from sqlalchemy import Column, Integer, String

from app.db.session import Base


class Supplier(Base):
    __tablename__ = "suppliers"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    region = Column(String, nullable=False)
    products_supplied = Column(String)  # TODO (Day 2): CSV string for now; revisit if a join table is needed
    status = Column(String, default="active")  # "active" | "on_hold"
