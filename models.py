from sqlalchemy import Column, Integer, String, ForeignKey, Boolean, DateTime, Float, Enum, Table
from sqlalchemy.orm import relationship
from database import Base
import datetime
import enum

class RoleEnum(str, enum.Enum):
    ADMIN = "Admin"
    OPERATOR = "Operator"
    AREA_MGR = "Area Mgr"
    STORE_MGR = "Store Mgr"
    CASHIER = "Cashier"

class TerminalStatus(str, enum.Enum):
    IDLE = "Idle"
    OCCUPIED = "Occupied"
    OFFLINE = "Offline"

class TransactionType(str, enum.Enum):
    DEPOSIT = "Deposit"
    WITHDRAW = "Withdraw"

# Association Table for Role <-> Permission
role_permissions = Table('role_permissions', Base.metadata,
    Column('role_id', Integer, ForeignKey('roles.id')),
    Column('permission_id', Integer, ForeignKey('permissions.id'))
)

class Permission(Base):
    __tablename__ = "permissions"
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, index=True) # e.g. USER_CREATE
    description = Column(String)

class Role(Base):
    __tablename__ = "roles"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True) # Admin, Store Mgr...
    permissions = relationship("Permission", secondary=role_permissions)

class SystemConfig(Base):
    __tablename__ = "system_config"
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, index=True)
    value = Column(String)
    description = Column(String, nullable=True)

class IPWhitelist(Base):
    __tablename__ = "ip_whitelist"
    id = Column(Integer, primary_key=True, index=True)
    ip_address = Column(String, unique=True)
    description = Column(String)
    # Scope: Global (outlet_id is NULL) or Specific Outlet
    outlet_id = Column(Integer, ForeignKey("outlets.id"), nullable=True)
    outlet = relationship("Outlet")

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    
    # RBAC
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=True)
    role = relationship("Role")
    
    # Relationships
    operator_id = Column(Integer, ForeignKey("operators.id"), nullable=True)
    outlet_id = Column(Integer, ForeignKey("outlets.id"), nullable=True) # For Store Mgr / Cashier

class Operator(Base):
    __tablename__ = "operators"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True)
    wallet_balance = Column(Float, default=0.0) # L1 -> L2 balance
    contact_person = Column(String, nullable=True)
    email = Column(String, nullable=True)
    
    outlets = relationship("Outlet", back_populates="operator")

class Outlet(Base):
    __tablename__ = "outlets"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    operator_id = Column(Integer, ForeignKey("operators.id"))
    bcf_balance = Column(Float, default=0.0) # L2 -> L3 balance
    address = Column(String, nullable=True)
    ip_whitelist = Column(String, nullable=True)
    
    operator = relationship("Operator", back_populates="outlets")
    terminals = relationship("Terminal", back_populates="outlet")
    wallets = relationship("Wallet", back_populates="outlet")

class Terminal(Base):
    __tablename__ = "terminals"
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True) # e.g., T-01
    outlet_id = Column(Integer, ForeignKey("outlets.id"))
    status = Column(String, default=TerminalStatus.IDLE) # TerminalStatus
    pairing_key = Column(String, nullable=True)
    hardware_id = Column(String, nullable=True)
    
    # Current Session Info
    current_player_id = Column(Integer, ForeignKey("players.id"), nullable=True)
    
    outlet = relationship("Outlet", back_populates="terminals")
    current_player = relationship("Player")

class Player(Base):
    __tablename__ = "players"
    id = Column(Integer, primary_key=True, index=True)
    phone = Column(String, unique=True, index=True)
    nickname = Column(String)
    
    wallets = relationship("Wallet", back_populates="player")

class Wallet(Base):
    __tablename__ = "wallets"
    id = Column(Integer, primary_key=True, index=True)
    player_id = Column(Integer, ForeignKey("players.id"))
    outlet_id = Column(Integer, ForeignKey("outlets.id"))
    balance = Column(Float, default=0.0)
    
    player = relationship("Player", back_populates="wallets")
    outlet = relationship("Outlet", back_populates="wallets")

class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    type = Column(String) # TransactionType
    amount = Column(Float)
    
    outlet_id = Column(Integer, ForeignKey("outlets.id"))
    terminal_id = Column(Integer, ForeignKey("terminals.id"), nullable=True)
    player_id = Column(Integer, ForeignKey("players.id"))
    staff_id = Column(Integer, ForeignKey("users.id"))

class BCFLog(Base):
    __tablename__ = "bcf_logs"
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    type = Column(String) # TopUp / Removal
    amount = Column(Float)
    from_user_id = Column(Integer, ForeignKey("users.id"))
    target_outlet_id = Column(Integer, ForeignKey("outlets.id"))
