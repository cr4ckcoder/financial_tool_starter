# app/models/domain.py
import enum
from sqlalchemy import (
    Column, Integer, String, ForeignKey, Numeric, Date, Text, Table
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

# --- Enums ---

class UserRole(str, enum.Enum):
    ADMIN = "ADMIN"
    STAFF = "STAFF"

class CompanyType(str, enum.Enum):
    PVT_LTD = 'PVT_LTD'
    LLP = 'LLP'
    PUBLIC_LTD = 'PUBLIC_LTD'

class WorkStatus(str, enum.Enum):
    PENDING = 'PENDING'
    IN_PROGRESS = 'IN_PROGRESS'
    COMPLETED = 'COMPLETED'

class AccountType(str, enum.Enum):
    CATEGORY = 'CATEGORY'
    HEAD = 'HEAD'
    SUB_HEAD = 'SUB_HEAD'

class CategoryType(str, enum.Enum):
    ASSET = 'ASSET'
    LIABILITY = 'LIABILITY'
    EQUITY = 'EQUITY'
    INCOME = 'INCOME'
    EXPENSE = 'EXPENSE'

# --- Association Table for RBAC ---
# Maps Staff Users to Companies they are allowed to access
user_company_association = Table(
    'user_company_association',
    Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id')),
    Column('company_id', Integer, ForeignKey('companies.id'))
)

# --- Auth Entities ---

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, default=UserRole.STAFF.value)
    
    # Assignments
    assigned_companies = relationship("Company", secondary=user_company_association, back_populates="assigned_staff")

# --- Core Entities ---

class Company(Base):
    __tablename__ = "companies"
    id = Column(Integer, primary_key=True, index=True)
    legal_name = Column(String, nullable=False, unique=True)
    cin = Column(String, unique=True)
    registered_address = Column(Text)
    company_type = Column(String) 
    
    works = relationship("FinancialWork", back_populates="company")
    assigned_staff = relationship("User", secondary=user_company_association, back_populates="assigned_companies")

class FinancialWork(Base):
    __tablename__ = "financial_works"
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    status = Column(String, default=WorkStatus.PENDING.value)
    
    company = relationship("Company", back_populates="works")
    trial_balance_entries = relationship("TrialBalanceEntry", back_populates="work")

class Account(Base):
    __tablename__ = "accounts"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)
    category_type = Column(String, nullable=False)
    
    parent_id = Column(Integer, ForeignKey('accounts.id'), nullable=True)
    children = relationship("Account", back_populates="parent")
    parent = relationship("Account", back_populates="children", remote_side=[id])

class TrialBalanceEntry(Base):
    __tablename__ = "trial_balance_entries"
    id = Column(Integer, primary_key=True, index=True)
    financial_work_id = Column(Integer, ForeignKey("financial_works.id"), nullable=False)
    account_name = Column(String, nullable=False)
    debit = Column(Numeric(15, 2), default=0)
    credit = Column(Numeric(15, 2), default=0)
    closing_balance = Column(Numeric(15, 2), nullable=False)
    
    work = relationship("FinancialWork", back_populates="trial_balance_entries")
    mapping = relationship("MappedLedgerEntry", uselist=False, back_populates="trial_balance_entry")

class MappedLedgerEntry(Base):
    __tablename__ = "mapped_ledger_entries"
    id = Column(Integer, primary_key=True, index=True)
    trial_balance_entry_id = Column(Integer, ForeignKey("trial_balance_entries.id"), unique=True, nullable=False)
    account_sub_head_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    
    trial_balance_entry = relationship("TrialBalanceEntry", back_populates="mapping")
    account_sub_head = relationship("Account")

class ReportTemplate(Base):
    __tablename__ = "report_templates"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    statement_type = Column(String, nullable=False)
    template_definition = Column(Text, nullable=False)