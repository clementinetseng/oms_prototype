from database import SessionLocal, engine
import models
from auth import get_password_hash

models.Base.metadata.drop_all(bind=engine)
models.Base.metadata.create_all(bind=engine)

db = SessionLocal()

def init_db():
    # 0. Create Permissions & Roles
    perms = {
        "DASHBOARD_VIEW": "View Dashboard",
        "POS_OPERATE": "Operate POS",
        "FINANCE_VIEW": "View Finance Reports",
        "BCF_MANAGE": "Manage BCF",
        "SETTINGS_MANAGE": "Manage Settings",
        "USER_CREATE": "Create Users"
    }
    
    perm_objs = {}
    for code, desc in perms.items():
        p = models.Permission(code=code, description=desc)
        db.add(p)
        perm_objs[code] = p
    db.commit()
    
    roles_def = {
        "Admin": ["DASHBOARD_VIEW", "POS_OPERATE", "FINANCE_VIEW", "BCF_MANAGE", "SETTINGS_MANAGE", "USER_CREATE"],
        "Operator": ["DASHBOARD_VIEW", "POS_OPERATE", "FINANCE_VIEW", "BCF_MANAGE", "SETTINGS_MANAGE", "USER_CREATE"],
        "Area Mgr": ["DASHBOARD_VIEW", "FINANCE_VIEW"],
        "Store Mgr": ["DASHBOARD_VIEW", "POS_OPERATE", "FINANCE_VIEW"],
        "Cashier": ["POS_OPERATE"]
    }
    
    role_objs = {}
    for r_name, p_codes in roles_def.items():
        role = models.Role(name=r_name)
        for code in p_codes:
            role.permissions.append(perm_objs[code])
        db.add(role)
        role_objs[r_name] = role
    db.commit()

    # 0.1 IP Whitelist
    ip = models.IPWhitelist(ip_address="127.0.0.1", description="Localhost")
    db.add(ip)
    db.commit()

    # 1. Create Operator
    op = models.Operator(name="MegaOperator", wallet_balance=1000000.0)
    db.add(op)
    db.commit()
    
    # 2. Create Outlet
    outlet = models.Outlet(name="Taipei Flagship Store", operator_id=op.id, bcf_balance=50000.0)
    db.add(outlet)
    db.commit()
    
    # 3. Create Terminals
    for i in range(1, 11):
        t = models.Terminal(
            code=f"OP1-TP-T{i:02d}", 
            name=f"{i}號機",
            outlet_id=outlet.id, 
            status=models.TerminalStatus.IDLE,
            is_active=True,
            is_paired=False
        )
        db.add(t)
    db.commit()
    
    # 4. Create Users
    # Admin
    admin = models.User(username="admin", hashed_password=get_password_hash("admin123"), role=role_objs["Admin"])
    db.add(admin)
    
    # Store Manager
    mgr = models.User(username="manager", hashed_password=get_password_hash("1234"), role=role_objs["Store Mgr"], outlet_id=outlet.id)
    db.add(mgr)
    
    # Cashier
    cashier = models.User(username="cashier", hashed_password=get_password_hash("1234"), role=role_objs["Cashier"], outlet_id=outlet.id)
    db.add(cashier)
    
    db.commit()
    print("Database initialized with seed data.")

if __name__ == "__main__":
    init_db()
