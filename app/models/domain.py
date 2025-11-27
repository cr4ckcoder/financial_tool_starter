from sqlalchemy import (
    Column, Integer, String, Enum, ForeignKey, Numeric, Date, Text
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class Company(Base):
    __tablename__ = "companies"
    id = Column(Integer, primary_key=True)
    legal_name = Column(String, nullable=False, unique=True)
    cin = Column(String, unique=True)
    registered_address = Column(Text)

class Account(Base):
    __tablename__ = "accounts"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)  # CATEGORY, HEAD, SUB_HEAD
    category_type = Column(String, nullable=False)  # ASSET, LIABILITY, ...
    parent_id = Column(Integer, ForeignKey('accounts.id'), nullable=True)
    parent = relationship("Account", remote_side=[id], backref="children")
