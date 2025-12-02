# app/models/domain.py
import enum
from sqlalchemy import (
    Column, Integer, String, ForeignKey, Numeric, Date, Text, Table, Boolean
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

# --- Enums ---

class UserRole(str, enum.Enum):
    ADMIN = "ADMIN"
    STAFF = "STAFF"

class ClientType(str, enum.Enum):
    PVT_LTD = 'PVT_LTD'
    PUBLIC_LTD = 'PUBLIC_LTD'
    LLP = 'LLP'
    TRUST = 'TRUST'
    SOCIETY = 'SOCIETY'
    PARTNERSHIP = 'PARTNERSHIP'
    PROPRIETORSHIP = 'PROPRIETORSHIP'
    INDIVIDUAL = 'INDIVIDUAL'
    AOP = 'AOP'

class Designation(str, enum.Enum):
    MD = 'Managing Director'
    DIRECTOR = 'Director'
    EXEC_DIR = 'Executive Director'
    IND_DIR = 'Independent Director'
    PARTNER = 'Partner'
    MANAGING_PARTNER = 'Managing Partner'
    PROPRIETOR = 'Proprietor'
    CEO = 'CEO'
    CFO = 'CFO'
    CS = 'Company Secretary'

class WorkStatus(str, enum.Enum):
    DRAFT = 'DRAFT'
    IN_PROGRESS = 'IN_PROGRESS'
    REVIEW = 'REVIEW'
    FINALIZED = 'FINALIZED'

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
    
    assigned_companies = relationship("Company", secondary=user_company_association, back_populates="assigned_staff")

# --- Master Data Entities ---

class Company(Base):
    __tablename__ = "companies"
    id = Column(Integer, primary_key=True, index=True)
    legal_name = Column(String, nullable=False, unique=True)
    
    # Expanded Metadata
    client_type = Column(String, nullable=False, default=ClientType.PVT_LTD.value)
    file_number = Column(String, nullable=True) # Physical file ref
    pan = Column(String(10), nullable=True)
    tan = Column(String(10), nullable=True)
    gstin = Column(String(15), nullable=True)
    
    cin = Column(String, unique=True, nullable=True)
    registered_address = Column(Text)
    
    works = relationship("FinancialWork", back_populates="company")
    assigned_staff = relationship("User", secondary=user_company_association, back_populates="assigned_companies")
    signatories = relationship("Signatory", back_populates="company")

class Signatory(Base):
    __tablename__ = "signatories"
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    
    name = Column(String, nullable=False)
    designation = Column(String, nullable=False) # Use Designation Enum
    din_number = Column(String, nullable=True)   # Director Identification Number
    pan_number = Column(String, nullable=True)
    
    # File Paths for Images
    photo_url = Column(String, nullable=True)
    id_proof_url = Column(String, nullable=True)
    
    is_active = Column(Boolean, default=True)
    
    company = relationship("Company", back_populates="signatories")

# --- Work & Financial Data ---

class FinancialWork(Base):
    __tablename__ = "financial_works"
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    
    # Compliance & Status
    status = Column(String, default=WorkStatus.DRAFT.value)
    signing_date = Column(Date, nullable=True)
    udin_number = Column(String, nullable=True)
    udin_certificate_url = Column(String, nullable=True)
    
    company = relationship("Company", back_populates="works")
    units = relationship("WorkUnit", back_populates="work")

class WorkUnit(Base):
    """
    Represents a specific branch or vertical. 
    If consolidation is not needed, a default 'Main' unit is used.
    """
    __tablename__ = "work_units"
    id = Column(Integer, primary_key=True, index=True)
    financial_work_id = Column(Integer, ForeignKey("financial_works.id"), nullable=False)
    unit_name = Column(String, nullable=False, default="Main")
    
    work = relationship("FinancialWork", back_populates="units")
    trial_balance_entries = relationship("TrialBalanceEntry", back_populates="unit")

class TrialBalanceEntry(Base):
    __tablename__ = "trial_balance_entries"
    id = Column(Integer, primary_key=True, index=True)
    
    # Linked to Unit now, not directly to Work
    work_unit_id = Column(Integer, ForeignKey("work_units.id"), nullable=False)
    
    # Versioning
    version_number = Column(Integer, default=1, nullable=False)
    
    account_name = Column(String, nullable=False)
    debit = Column(Numeric(15, 2), default=0)
    credit = Column(Numeric(15, 2), default=0)
    closing_balance = Column(Numeric(15, 2), nullable=False)
    
    unit = relationship("WorkUnit", back_populates="trial_balance_entries")
    mapping = relationship("MappedLedgerEntry", uselist=False, back_populates="trial_balance_entry")

class Account(Base):
    __tablename__ = "accounts"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)
    category_type = Column(String, nullable=False)
    
    parent_id = Column(Integer, ForeignKey('accounts.id'), nullable=True)
    children = relationship("Account", back_populates="parent")
    parent = relationship("Account", back_populates="children", remote_side=[id])

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
    # Smart Format: Auto-suggest based on client type
    applicable_client_types = Column(Text, nullable=True) # JSON list of types, e.g. ["PVT_LTD", "LLP"]
    template_definition = Column(Text, nullable=False)

class WorkReportConfiguration(Base):
    __tablename__ = "work_report_configurations"
    id = Column(Integer, primary_key=True, index=True)
    financial_work_id = Column(Integer, ForeignKey("financial_works.id"), nullable=False, unique=True)
    custom_notes = Column(Text, default="{}")
    
    # New: Selected Signatories for reports
    selected_signatories = Column(Text, default="[]") # JSON list of signatory_ids
    
    work = relationship("FinancialWork", backref="report_configuration")
    
    
class OrganizationSettings(Base):
    __tablename__ = "organization_settings"
    id = Column(Integer, primary_key=True, index=True)
    firm_name = Column(String, nullable=False, default="My CA Firm")
    firm_registration_number = Column(String, nullable=True)
    address = Column(Text, nullable=True)
    city = Column(String, nullable=True)
    pincode = Column(String, nullable=True)
    email = Column(String, nullable=True)
    pan = Column(String, nullable=True)  # <--- NEW FIELD
    logo_url = Column(String, nullable=True)
    
class ComplianceTemplate(Base):
    __tablename__ = "compliance_templates"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    content_html = Column(Text, nullable=True) # Legacy support
    
    # NEW: Stores JSON list of blocks e.g. [{"type": "text", "content": "..."}, {"type": "signatories"}]
    template_definition = Column(Text, nullable=True)