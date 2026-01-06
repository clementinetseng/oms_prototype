from fastapi import FastAPI, Depends, HTTPException, status, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import List, Optional
import models, schemas, auth
from database import engine, get_db
from datetime import timedelta
import os

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="OMS Prototype")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

# --- API Endpoints ---

@app.post("/token", response_model=schemas.Token)
async def login_for_access_token(request: Request, form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # 1. IP Check
    await auth.check_ip_whitelist(request, db)

    # 2. Auth
    user = db.query(models.User).options(auth.joinedload(models.User.role)).filter(models.User.username == form_data.username).first()
    if not user or not auth.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    role_name = user.role.name if user.role else "Unknown"
    
    access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": user.username, "role": role_name, "outlet_id": user.outlet_id}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer", "role": role_name, "outlet_id": user.outlet_id}

# --- Settings APIs ---

@app.get("/api/settings/ip_whitelist", response_model=List[schemas.IPWhitelistOut])
def get_ip_whitelist(current_user: models.User = Depends(auth.require_permission("SETTINGS_MANAGE")), db: Session = Depends(get_db)):
    return db.query(models.IPWhitelist).all()

@app.post("/api/settings/ip_whitelist", response_model=schemas.IPWhitelistOut)
def create_ip_whitelist(ip: schemas.IPWhitelistCreate, current_user: models.User = Depends(auth.require_permission("SETTINGS_MANAGE")), db: Session = Depends(get_db)):
    db_ip = models.IPWhitelist(**ip.dict())
    db.add(db_ip)
    db.commit()
    db.refresh(db_ip)
    return db_ip

@app.delete("/api/settings/ip_whitelist/{id}")
def delete_ip_whitelist(id: int, current_user: models.User = Depends(auth.require_permission("SETTINGS_MANAGE")), db: Session = Depends(get_db)):
    db.query(models.IPWhitelist).filter(models.IPWhitelist.id == id).delete()
    db.commit()
    return {"message": "Deleted"}

@app.get("/api/settings/config")
def get_system_config(current_user: models.User = Depends(auth.require_permission("SETTINGS_MANAGE")), db: Session = Depends(get_db)):
    return db.query(models.SystemConfig).all()

@app.post("/api/settings/config")
def update_system_config(key: str = Form(...), value: str = Form(...), current_user: models.User = Depends(auth.require_permission("SETTINGS_MANAGE")), db: Session = Depends(get_db)):
    config = db.query(models.SystemConfig).filter(models.SystemConfig.key == key).first()
    if config:
        config.value = value
    else:
        config = models.SystemConfig(key=key, value=value)
        db.add(config)
    db.commit()
    return {"message": "Config updated", "key": key, "value": value}

# --- Terminal Management ---

@app.delete("/api/terminals/{id}")
def delete_terminal(id: int, current_user: models.User = Depends(auth.require_permission("SETTINGS_MANAGE")), db: Session = Depends(get_db)):
    db.query(models.Terminal).filter(models.Terminal.id == id).delete()
    db.commit()
    return {"message": "Deleted"}

@app.get("/api/roles", response_model=List[schemas.RoleOut])
def get_roles(current_user: models.User = Depends(auth.require_permission("USER_CREATE")), db: Session = Depends(get_db)):
    return db.query(models.Role).options(auth.joinedload(models.Role.permissions)).all()

@app.get("/api/permissions", response_model=List[schemas.PermissionOut])
def get_permissions(current_user: models.User = Depends(auth.require_permission("USER_CREATE")), db: Session = Depends(get_db)):
    return db.query(models.Permission).all()

@app.put("/api/roles/{role_id}")
def update_role(role_id: int, role_data: schemas.RoleCreate, current_user: models.User = Depends(auth.require_permission("USER_CREATE")), db: Session = Depends(get_db)):
    role = db.query(models.Role).filter(models.Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    
    # Update Name
    if role_data.name != role.name:
        existing = db.query(models.Role).filter(models.Role.name == role_data.name).first()
        if existing:
            raise HTTPException(status_code=400, detail="Role name already exists")
        role.name = role_data.name

    # Update Permissions
    role.permissions = []
    for p_id in role_data.permission_ids:
        perm = db.query(models.Permission).filter(models.Permission.id == p_id).first()
        if perm:
            role.permissions.append(perm)
            
    db.commit()
    db.refresh(role)
    return role

@app.delete("/api/roles/{role_id}")
def delete_role(role_id: int, current_user: models.User = Depends(auth.require_permission("USER_CREATE")), db: Session = Depends(get_db)):
    role = db.query(models.Role).filter(models.Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    
    # Check if used
    users_count = db.query(models.User).filter(models.User.role_id == role_id).count()
    if users_count > 0:
        raise HTTPException(status_code=400, detail="Cannot delete role assigned to users")
        
    db.delete(role)
    db.commit()
    return {"message": "Role deleted"}

@app.post("/api/roles", response_model=schemas.RoleOut)
def create_role(role: schemas.RoleCreate, current_user: models.User = Depends(auth.require_permission("USER_CREATE")), db: Session = Depends(get_db)):
    # Check if role exists
    existing = db.query(models.Role).filter(models.Role.name == role.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Role already exists")
    
    new_role = models.Role(name=role.name)
    
    # Add permissions
    for p_id in role.permission_ids:
        perm = db.query(models.Permission).filter(models.Permission.id == p_id).first()
        if perm:
            new_role.permissions.append(perm)
            
    db.add(new_role)
    db.commit()
    db.refresh(new_role)
    return new_role

@app.get("/api/users", response_model=List[schemas.UserOut])
def get_users(current_user: models.User = Depends(auth.require_permission("USER_CREATE")), db: Session = Depends(get_db)):
    query = db.query(models.User).options(auth.joinedload(models.User.role))
    
    # Scope Guard: Filter users based on hierarchy
    if current_user.role.name == "Operator":
        # Can see users in their operator scope (including themselves, or their staff)
        # For simplicity, let's say they can see users linked to their outlets or operator_id
        # But User model has operator_id.
        query = query.filter(models.User.operator_id == current_user.operator_id)
    elif current_user.role.name == "Store Mgr":
        query = query.filter(models.User.outlet_id == current_user.outlet_id)
    
    return query.all()

@app.post("/api/users", response_model=schemas.UserOut)
def create_user(user: schemas.UserCreate, current_user: models.User = Depends(auth.require_permission("USER_CREATE")), db: Session = Depends(get_db)):
    # 1. Level Guard
    target_role = db.query(models.Role).filter(models.Role.id == user.role_id).first()
    if not target_role:
        raise HTTPException(status_code=400, detail="Role not found")
    
    creator_role = current_user.role.name
    allowed_creation = {
        "Admin": ["Admin", "Operator", "Area Mgr", "Store Mgr", "Cashier"],
        "Operator": ["Area Mgr", "Store Mgr", "Cashier"],
        "Store Mgr": ["Cashier"]
    }
    
    if target_role.name not in allowed_creation.get(creator_role, []):
        raise HTTPException(status_code=403, detail=f"Level Guard: {creator_role} cannot create {target_role.name}")

    # 2. Scope Guard & Auto-Assign
    final_operator_id = None
    final_outlet_id = user.outlet_id
    
    if creator_role == "Operator":
        final_operator_id = current_user.operator_id
        # Ensure outlet belongs to this operator
        if final_outlet_id:
            outlet = db.query(models.Outlet).filter(models.Outlet.id == final_outlet_id, models.Outlet.operator_id == final_operator_id).first()
            if not outlet:
                raise HTTPException(status_code=400, detail="Scope Guard: Outlet not found in your scope")
    elif creator_role == "Store Mgr":
        final_outlet_id = current_user.outlet_id # Force lock
        final_operator_id = current_user.operator_id # Inherit
    
    db_user = models.User(
        username=user.username,
        hashed_password=auth.get_password_hash(user.password),
        role_id=user.role_id,
        outlet_id=final_outlet_id,
        operator_id=final_operator_id
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@app.put("/api/users/{id}", response_model=schemas.UserOut)
def update_user(id: int, user: schemas.UserCreate, current_user: models.User = Depends(auth.require_permission("USER_CREATE")), db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.id == id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Simple scope check (can be improved)
    if current_user.role.name == "Operator" and db_user.operator_id != current_user.operator_id:
         raise HTTPException(status_code=403, detail="Not in your scope")
         
    db_user.username = user.username
    if user.password:
        db_user.hashed_password = auth.get_password_hash(user.password)
    db_user.role_id = user.role_id
    db_user.outlet_id = user.outlet_id
    db_user.operator_id = user.operator_id
    
    db.commit()
    db.refresh(db_user)
    return db_user

@app.get("/api/operators", response_model=List[schemas.OperatorOut])
def get_operators(current_user: models.User = Depends(auth.require_permission("SETTINGS_MANAGE")), db: Session = Depends(get_db)):
    if current_user.role.name != "Admin":
        raise HTTPException(status_code=403, detail="Only Admin can view operators")
    return db.query(models.Operator).all()

@app.post("/api/operators", response_model=schemas.OperatorOut)
def create_operator(op: schemas.OperatorCreate, current_user: models.User = Depends(auth.require_permission("SETTINGS_MANAGE")), db: Session = Depends(get_db)):
    if current_user.role.name != "Admin":
        raise HTTPException(status_code=403, detail="Only Admin can create operators")
    db_op = models.Operator(
        name=op.name, 
        wallet_balance=op.wallet_balance,
        contact_person=op.contact_person,
        email=op.email
    )
    db.add(db_op)
    db.commit()
    db.refresh(db_op)
    return db_op

@app.put("/api/operators/{id}", response_model=schemas.OperatorOut)
def update_operator(id: int, op: schemas.OperatorCreate, current_user: models.User = Depends(auth.require_permission("SETTINGS_MANAGE")), db: Session = Depends(get_db)):
    if current_user.role.name != "Admin":
        raise HTTPException(status_code=403, detail="Only Admin can update operators")
    
    db_op = db.query(models.Operator).filter(models.Operator.id == id).first()
    if not db_op:
        raise HTTPException(status_code=404, detail="Operator not found")
    
    db_op.name = op.name
    db_op.wallet_balance = op.wallet_balance
    db_op.contact_person = op.contact_person
    db_op.email = op.email
    
    db.commit()
    db.refresh(db_op)
    return db_op

@app.get("/api/outlets", response_model=List[schemas.OutletOut])
def get_outlets(current_user: models.User = Depends(auth.require_permission("SETTINGS_MANAGE")), db: Session = Depends(get_db)):
    query = db.query(models.Outlet)
    if current_user.role.name == "Operator":
        query = query.filter(models.Outlet.operator_id == current_user.operator_id)
    elif current_user.role.name != "Admin":
        # Store Mgr / Cashier / Area Mgr?
        # Area Mgr can view multiple, Store Mgr view single
        if current_user.outlet_id:
             query = query.filter(models.Outlet.id == current_user.outlet_id)
        else:
             return [] # Should not happen for Store Mgr
    return query.all()

@app.post("/api/outlets", response_model=schemas.OutletOut)
def create_outlet(outlet: schemas.OutletCreate, current_user: models.User = Depends(auth.require_permission("SETTINGS_MANAGE")), db: Session = Depends(get_db)):
    # Admin or Operator
    if current_user.role.name not in ["Admin", "Operator"]:
        raise HTTPException(status_code=403, detail="Permission denied")
    
    op_id = outlet.operator_id
    if current_user.role.name == "Operator":
        op_id = current_user.operator_id # Force own scope
    
    db_outlet = models.Outlet(
        name=outlet.name, 
        operator_id=op_id, 
        bcf_balance=outlet.bcf_balance,
        address=outlet.address,
        ip_whitelist=outlet.ip_whitelist
    )
    db.add(db_outlet)
    db.commit()
    db.refresh(db_outlet)
    return db_outlet

@app.put("/api/outlets/{id}", response_model=schemas.OutletOut)
def update_outlet(id: int, outlet: schemas.OutletCreate, current_user: models.User = Depends(auth.require_permission("SETTINGS_MANAGE")), db: Session = Depends(get_db)):
    if current_user.role.name not in ["Admin", "Operator"]:
        raise HTTPException(status_code=403, detail="Permission denied")
    
    db_outlet = db.query(models.Outlet).filter(models.Outlet.id == id).first()
    if not db_outlet:
        raise HTTPException(status_code=404, detail="Outlet not found")
        
    # Scope check
    if current_user.role.name == "Operator" and db_outlet.operator_id != current_user.operator_id:
        raise HTTPException(status_code=403, detail="Not in your scope")

    db_outlet.name = outlet.name
    db_outlet.bcf_balance = outlet.bcf_balance
    db_outlet.address = outlet.address
    db_outlet.ip_whitelist = outlet.ip_whitelist
    # Operator ID usually shouldn't change, but if Admin wants to move it? Let's allow if Admin.
    if current_user.role.name == "Admin" and outlet.operator_id:
        db_outlet.operator_id = outlet.operator_id
    
    db.commit()
    db.refresh(db_outlet)
    return db_outlet

@app.get("/api/dashboard", response_model=schemas.OutletStats)
def get_dashboard_stats(current_user: models.User = Depends(auth.require_permission("DASHBOARD_VIEW")), db: Session = Depends(get_db)):
    if not current_user.outlet_id:
        # Admin/Operator view (Mock aggregate)
        return {"bcf_balance": 999999.0, "active_terminals": 10, "total_turnover": 50000.0, "total_ggr": 5000.0, "net_cash": 10000.0}
    
    outlet = db.query(models.Outlet).filter(models.Outlet.id == current_user.outlet_id).first()
    active_terminals = db.query(models.Terminal).filter(models.Terminal.outlet_id == outlet.id, models.Terminal.status != models.TerminalStatus.OFFLINE).count()
    
    # Mock financial stats for prototype
    return {
        "bcf_balance": outlet.bcf_balance,
        "active_terminals": active_terminals,
        "total_turnover": 12000.0,
        "total_ggr": 1200.0,
        "net_cash": 5000.0
    }

@app.get("/api/terminals", response_model=List[schemas.TerminalOut])
def get_terminals(current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    query = db.query(models.Terminal)
    
    if current_user.role.name == "Admin":
        pass # See all
    elif current_user.role.name == "Operator":
        # See all terminals in their outlets
        query = query.join(models.Outlet).filter(models.Outlet.operator_id == current_user.operator_id)
    elif current_user.outlet_id:
        query = query.filter(models.Terminal.outlet_id == current_user.outlet_id)
    else:
        return []

    terminals = query.all()
    result = []
    for t in terminals:
        p_name = None
        p_bal = None
        if t.current_player_id:
            player = db.query(models.Player).filter(models.Player.id == t.current_player_id).first()
            if player:
                p_name = player.nickname
                wallet = db.query(models.Wallet).filter(models.Wallet.player_id == player.id, models.Wallet.outlet_id == t.outlet_id).first()
                p_bal = wallet.balance if wallet else 0.0
        
        result.append({
            "id": t.id,
            "code": t.code,
            "status": t.status,
            "pairing_key": t.pairing_key,
            "outlet_id": t.outlet_id,
            "current_player_name": p_name,
            "current_balance": p_bal
        })
    return result

@app.post("/api/terminals", response_model=schemas.TerminalOut)
def create_terminal(term: schemas.TerminalCreate, current_user: models.User = Depends(auth.require_permission("SETTINGS_MANAGE")), db: Session = Depends(get_db)):
    # Check permissions
    if current_user.role.name not in ["Admin", "Operator"]:
        raise HTTPException(status_code=403, detail="Permission denied")
        
    # Check outlet scope
    if current_user.role.name == "Operator":
        outlet = db.query(models.Outlet).filter(models.Outlet.id == term.outlet_id, models.Outlet.operator_id == current_user.operator_id).first()
        if not outlet:
            raise HTTPException(status_code=400, detail="Outlet not in scope")
            
    import secrets
    pairing_key = secrets.token_hex(4).upper()
    
    db_term = models.Terminal(
        code=term.code,
        outlet_id=term.outlet_id,
        pairing_key=pairing_key,
        status=models.TerminalStatus.IDLE,
        hardware_id=term.hardware_id
    )
    db.add(db_term)
    db.commit()
    db.refresh(db_term)
    
    return {
        "id": db_term.id,
        "code": db_term.code,
        "status": db_term.status,
        "pairing_key": db_term.pairing_key,
        "outlet_id": db_term.outlet_id,
        "current_player_name": None,
        "current_balance": None
    }

@app.post("/api/bind_terminal")
def bind_terminal(terminal_id: int = Form(...), phone: str = Form(...), current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    # 1. Find Terminal
    terminal = db.query(models.Terminal).filter(models.Terminal.id == terminal_id, models.Terminal.outlet_id == current_user.outlet_id).first()
    if not terminal or terminal.status != models.TerminalStatus.IDLE:
        raise HTTPException(status_code=400, detail="Terminal not available")
    
    # 2. Find Player
    player = db.query(models.Player).filter(models.Player.phone == phone).first()
    if not player:
        # Auto create for prototype
        player = models.Player(phone=phone, nickname=f"Player_{phone[-4:]}")
        db.add(player)
        db.commit()
        db.refresh(player)
    
    # 3. Check/Create Wallet
    wallet = db.query(models.Wallet).filter(models.Wallet.player_id == player.id, models.Wallet.outlet_id == current_user.outlet_id).first()
    if not wallet:
        wallet = models.Wallet(player_id=player.id, outlet_id=current_user.outlet_id, balance=0.0)
        db.add(wallet)
        db.commit()
    
    # 4. Bind
    terminal.status = models.TerminalStatus.OCCUPIED
    terminal.current_player_id = player.id
    db.commit()
    return {"message": "Terminal bound successfully", "player": player.nickname, "balance": wallet.balance}

@app.post("/api/deposit")
def deposit(req: schemas.DepositRequest, current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    # 1. Check BCF
    outlet = db.query(models.Outlet).filter(models.Outlet.id == current_user.outlet_id).first()
    if outlet.bcf_balance < req.amount:
        raise HTTPException(status_code=400, detail="Insufficient BCF Balance")
    
    terminal = db.query(models.Terminal).filter(models.Terminal.id == req.terminal_id).first()
    if not terminal or not terminal.current_player_id:
        raise HTTPException(status_code=400, detail="Terminal not active")
        
    wallet = db.query(models.Wallet).filter(models.Wallet.player_id == terminal.current_player_id, models.Wallet.outlet_id == current_user.outlet_id).first()
    
    # 2. Transaction
    outlet.bcf_balance -= req.amount
    wallet.balance += req.amount
    
    txn = models.Transaction(
        type=models.TransactionType.DEPOSIT,
        amount=req.amount,
        outlet_id=outlet.id,
        terminal_id=terminal.id,
        player_id=terminal.current_player_id,
        staff_id=current_user.id
    )
    db.add(txn)
    db.commit()
    return {"message": "Deposit successful", "new_balance": wallet.balance}

@app.post("/api/settle")
def settle(req: schemas.SettleRequest, current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    terminal = db.query(models.Terminal).filter(models.Terminal.id == req.terminal_id).first()
    if not terminal or not terminal.current_player_id:
        raise HTTPException(status_code=400, detail="Terminal not active")
    
    wallet = db.query(models.Wallet).filter(models.Wallet.player_id == terminal.current_player_id, models.Wallet.outlet_id == current_user.outlet_id).first()
    amount_to_return = wallet.balance
    
    # 1. Zero Balance
    outlet = db.query(models.Outlet).filter(models.Outlet.id == current_user.outlet_id).first()
    outlet.bcf_balance += amount_to_return
    wallet.balance = 0.0
    
    # 2. Log
    txn = models.Transaction(
        type=models.TransactionType.WITHDRAW,
        amount=amount_to_return,
        outlet_id=outlet.id,
        terminal_id=terminal.id,
        player_id=terminal.current_player_id,
        staff_id=current_user.id
    )
    db.add(txn)
    
    # 3. Unbind
    terminal.status = models.TerminalStatus.IDLE
    terminal.current_player_id = None
    
    db.commit()
    return {"message": "Settled successfully", "returned_cash": amount_to_return}

# --- Web Pages ---

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/dashboard", response_class=HTMLResponse)
async def view_dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.get("/pos", response_class=HTMLResponse)
async def view_pos(request: Request):
    return templates.TemplateResponse("pos.html", {"request": request})

@app.get("/settings", response_class=HTMLResponse)
async def view_settings(request: Request):
    return templates.TemplateResponse("settings.html", {"request": request})

@app.get("/announcements", response_class=HTMLResponse)
async def view_announcements(request: Request):
    return templates.TemplateResponse("announcements.html", {"request": request})

@app.get("/announcements/new", response_class=HTMLResponse)
async def view_announcement_form(request: Request):
    return templates.TemplateResponse("announcement_form.html", {"request": request})

@app.get("/machines", response_class=HTMLResponse)
async def view_machines(request: Request):
    return templates.TemplateResponse("machines.html", {"request": request})

@app.get("/org/staff", response_class=HTMLResponse)
async def view_staff_list(request: Request):
    return templates.TemplateResponse("staff_list.html", {"request": request})

@app.get("/org/staff/add", response_class=HTMLResponse)
async def view_staff_add(request: Request):
    return templates.TemplateResponse("staff_add.html", {"request": request})

@app.get("/org/operators", response_class=HTMLResponse)
async def view_operator_list(request: Request):
    return templates.TemplateResponse("operator_list.html", {"request": request})

@app.get("/org/operators/add", response_class=HTMLResponse)
async def view_operator_add(request: Request):
    return templates.TemplateResponse("operator_add.html", {"request": request})

@app.get("/org/outlets", response_class=HTMLResponse)
async def view_outlet_list(request: Request):
    return templates.TemplateResponse("outlet_list.html", {"request": request})

@app.get("/org/outlets/add", response_class=HTMLResponse)
async def view_outlet_add(request: Request):
    return templates.TemplateResponse("outlet_add.html", {"request": request})

@app.get("/roles", response_class=HTMLResponse)
async def view_roles(request: Request):
    return templates.TemplateResponse("roles.html", {"request": request})
