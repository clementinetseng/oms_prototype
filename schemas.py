from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class UserLogin(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    role: str
    outlet_id: Optional[int] = None

class PermissionOut(BaseModel):
    id: int
    code: str
    description: str
    class Config:
        from_attributes = True

class RoleUpdatePermissions(BaseModel):
    permission_ids: List[int]

class RoleCreate(BaseModel):
    name: str
    permission_ids: List[int] = []

class RoleOut(BaseModel):
    id: int
    name: str
    permissions: List[PermissionOut] = []
    class Config:
        from_attributes = True

class IPWhitelistCreate(BaseModel):
    ip_address: str
    description: str
    outlet_id: Optional[int] = None

class IPWhitelistOut(IPWhitelistCreate):
    id: int
    class Config:
        from_attributes = True

class UserCreate(BaseModel):
    username: str
    password: str
    role_id: int
    outlet_id: Optional[int] = None

class UserOut(BaseModel):
    id: int
    username: str
    role: Optional[RoleOut] = None
    outlet_id: Optional[int] = None
    class Config:
        from_attributes = True

class OperatorCreate(BaseModel):
    name: str
    wallet_balance: float = 0.0
    contact_person: Optional[str] = None
    email: Optional[str] = None

class OperatorOut(OperatorCreate):
    id: int
    class Config:
        from_attributes = True

class OutletCreate(BaseModel):
    name: str
    operator_id: Optional[int] = None
    bcf_balance: float = 0.0
    address: Optional[str] = None
    ip_whitelist: Optional[str] = None

class OutletOut(OutletCreate):
    id: int
    class Config:
        from_attributes = True

class TerminalCreate(BaseModel):
    name: str
    outlet_id: int
    is_active: bool = True

class TerminalOut(BaseModel):
    id: int
    code: str
    name: Optional[str]
    outlet_id: int
    status: str
    is_active: bool
    is_paired: bool
    last_seen: Optional[datetime]
    hardware_id: Optional[str]
    
    class Config:
        from_attributes = True

class PlayerSearch(BaseModel):
    phone: str

class PlayerInfo(BaseModel):
    id: int
    phone: str
    nickname: str
    balance: float # Local wallet balance

class DepositRequest(BaseModel):
    terminal_id: int
    amount: float

class SettleRequest(BaseModel):
    terminal_id: int

class TerminalOut(BaseModel):
    id: int
    code: str
    status: str
    pairing_key: Optional[str] = None
    outlet_id: Optional[int] = None
    current_player_name: Optional[str] = None
    current_balance: Optional[float] = None
    class Config:
        from_attributes = True
    pairing_key: Optional[str] = None

class TerminalCreate(BaseModel):
    code: str
    outlet_id: int

class TerminalBind(BaseModel):
    pairing_key: str
    hardware_id: str

class OutletStats(BaseModel):
    bcf_balance: float
    active_terminals: int
    total_turnover: float = 0.0 # Mock
    total_ggr: float = 0.0 # Mock
    net_cash: float = 0.0 # Mock
