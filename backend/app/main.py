from datetime import datetime, timedelta
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func
from sqlalchemy.orm import Session
from .database import Base, engine, get_db, settings
from .dependencies import get_current_user, require_roles
from .models import Assignment, AuditLog, Asset, BaseLocation, EquipmentType, Expenditure, Purchase, Role, Transfer, User
from .schemas import AssignmentCreate, ExpenditureCreate, LoginRequest, PurchaseCreate, TokenResponse, TransferCreate
from .security import create_access_token, verify_password

Base.metadata.create_all(bind=engine)
app = FastAPI(title="Military Asset Management API", version="1.0.0")
origins = [x.strip() for x in settings.cors_origins.split(",") if x.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins or ["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

def audit(db: Session, user: User, action: str, entity: str, entity_id: int | None, details: str = ""):
    db.add(AuditLog(user_id=user.id, action=action, entity=entity, entity_id=entity_id, details=details))

def base_allowed(user: User, base_id: int) -> bool:
    return user.role.name != "BASE_COMMANDER" or user.base_id == base_id

def asset_allowed(user: User, asset: Asset) -> bool:
    return user.role.name != "BASE_COMMANDER" or user.base_id == asset.base_id

@app.get("/api/health")
def health():
    return {"status": "ok"}

@app.post("/api/auth/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == body.username).first()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    token = create_access_token({"sub": str(user.id), "role": user.role.name})
    return {"access_token": token, "token_type": "bearer", "user": {"id": user.id, "username": user.username, "full_name": user.full_name, "role": user.role.name, "base_id": user.base_id}}

@app.get("/api/me")
def me(user: User = Depends(get_current_user)):
    return {"id": user.id, "username": user.username, "full_name": user.full_name, "role": user.role.name, "base_id": user.base_id}

@app.get("/api/bases")
def bases(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    q = db.query(BaseLocation)
    if user.role.name == "BASE_COMMANDER": q = q.filter(BaseLocation.id == user.base_id)
    return [{"id": b.id, "name": b.name, "location": b.location} for b in q.order_by(BaseLocation.name).all()]

@app.get("/api/equipment-types")
def equipment_types(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return [{"id": e.id, "name": e.name, "category": e.category} for e in db.query(EquipmentType).order_by(EquipmentType.name).all()]

@app.get("/api/assets")
def assets(db: Session = Depends(get_db), user: User = Depends(get_current_user), base_id: int | None = None, equipment_type_id: int | None = None):
    q = db.query(Asset)
    if user.role.name == "BASE_COMMANDER": q = q.filter(Asset.base_id == user.base_id)
    elif base_id: q = q.filter(Asset.base_id == base_id)
    if equipment_type_id: q = q.filter(Asset.equipment_type_id == equipment_type_id)
    rows = q.order_by(Asset.id.desc()).all()
    return [{"id": a.id, "asset_code": a.asset_code, "equipment_type": a.equipment_type.name, "equipment_type_id": a.equipment_type_id, "base": a.base.name, "base_id": a.base_id, "status": a.status, "quantity": a.quantity} for a in rows]

@app.get("/api/dashboard")
def dashboard(db: Session = Depends(get_db), user: User = Depends(get_current_user), date_from: datetime | None = None, date_to: datetime | None = None, base_id: int | None = None, equipment_type_id: int | None = None):
    if user.role.name == "BASE_COMMANDER": base_id = user.base_id
    # Work out the dashboard values from the saved transactions.
    purchase_q = db.query(func.coalesce(func.sum(Purchase.quantity), 0)).filter(True)
    if base_id: purchase_q = purchase_q.filter(Purchase.base_id == base_id)
    if equipment_type_id: purchase_q = purchase_q.filter(Purchase.equipment_type_id == equipment_type_id)
    if date_from: purchase_q = purchase_q.filter(Purchase.purchase_date >= date_from)
    if date_to: purchase_q = purchase_q.filter(Purchase.purchase_date <= date_to)
    purchases = int(purchase_q.scalar() or 0)

    transfer_in_q = db.query(func.coalesce(func.sum(Transfer.quantity), 0)).filter(True)
    transfer_out_q = db.query(func.coalesce(func.sum(Transfer.quantity), 0)).filter(True)
    if base_id:
        transfer_in_q = transfer_in_q.filter(Transfer.to_base_id == base_id)
        transfer_out_q = transfer_out_q.filter(Transfer.from_base_id == base_id)
    if date_from:
        transfer_in_q = transfer_in_q.filter(Transfer.transferred_at >= date_from); transfer_out_q = transfer_out_q.filter(Transfer.transferred_at >= date_from)
    if date_to:
        transfer_in_q = transfer_in_q.filter(Transfer.transferred_at <= date_to); transfer_out_q = transfer_out_q.filter(Transfer.transferred_at <= date_to)
    transfer_in = int(transfer_in_q.scalar() or 0); transfer_out = int(transfer_out_q.scalar() or 0)

    asset_q = db.query(Asset)
    if base_id: asset_q = asset_q.filter(Asset.base_id == base_id)
    if equipment_type_id: asset_q = asset_q.filter(Asset.equipment_type_id == equipment_type_id)
    current_total = int(sum(a.quantity for a in asset_q.all()))
    expenditure_q = db.query(func.coalesce(func.sum(Expenditure.quantity), 0)).join(Asset).filter(True)
    if base_id: expenditure_q = expenditure_q.filter(Asset.base_id == base_id)
    if equipment_type_id: expenditure_q = expenditure_q.filter(Asset.equipment_type_id == equipment_type_id)
    if date_from: expenditure_q = expenditure_q.filter(Expenditure.expended_at >= date_from)
    if date_to: expenditure_q = expenditure_q.filter(Expenditure.expended_at <= date_to)
    expended = int(expenditure_q.scalar() or 0)
    opening = max(current_total - purchases - transfer_in + transfer_out + expended, 0)
    closing = current_total
    return {"opening_balance": opening, "purchases": purchases, "transfer_in": transfer_in, "transfer_out": transfer_out, "net_movement": purchases + transfer_in - transfer_out, "assigned_assets": int(db.query(func.coalesce(func.sum(Assignment.quantity), 0)).scalar() or 0), "expended_assets": expended, "closing_balance": closing}

@app.get("/api/dashboard/net-movement")
def net_movement_details(db: Session = Depends(get_db), user: User = Depends(get_current_user), base_id: int | None = None):
    if user.role.name == "BASE_COMMANDER": base_id = user.base_id
    pq = db.query(Purchase).order_by(Purchase.purchase_date.desc())
    ti = db.query(Transfer).order_by(Transfer.transferred_at.desc())
    if base_id: pq = pq.filter(Purchase.base_id == base_id); ti = ti.filter((Transfer.from_base_id == base_id) | (Transfer.to_base_id == base_id))
    return {"purchases": [{"date": p.purchase_date, "quantity": p.quantity, "base": p.base.name, "equipment_type": p.equipment_type.name} for p in pq.limit(50).all()], "transfers": [{"date": t.transferred_at, "quantity": t.quantity, "from": t.from_base.name, "to": t.to_base.name} for t in ti.limit(50).all()]}

@app.post("/api/purchases")
def create_purchase(body: PurchaseCreate, db: Session = Depends(get_db), user: User = Depends(require_roles("ADMIN", "LOGISTICS_OFFICER", "BASE_COMMANDER"))):
    if not base_allowed(user, body.base_id): raise HTTPException(403, "Base access denied")
    if body.quantity <= 0: raise HTTPException(400, "Quantity must be positive")
    p = Purchase(base_id=body.base_id, equipment_type_id=body.equipment_type_id, quantity=body.quantity, unit_cost=body.unit_cost, purchase_date=body.purchase_date or datetime.utcnow(), reference=body.reference)
    db.add(p); db.flush()
    asset_code = f"AST-{body.base_id}-{body.equipment_type_id}-{int(datetime.utcnow().timestamp())}-{p.id}"
    a = Asset(asset_code=asset_code, equipment_type_id=body.equipment_type_id, base_id=body.base_id, quantity=body.quantity, purchase_cost=body.unit_cost)
    db.add(a); db.flush(); audit(db, user, "CREATE", "PURCHASE", p.id, f"quantity={body.quantity}"); db.commit()
    return {"message": "Purchase recorded", "purchase_id": p.id, "asset_id": a.id}

@app.get("/api/purchases")
def list_purchases(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    q = db.query(Purchase).order_by(Purchase.purchase_date.desc())
    if user.role.name == "BASE_COMMANDER": q = q.filter(Purchase.base_id == user.base_id)
    return [{"id": p.id, "base": p.base.name, "equipment_type": p.equipment_type.name, "quantity": p.quantity, "unit_cost": float(p.unit_cost or 0), "purchase_date": p.purchase_date, "reference": p.reference} for p in q.limit(100).all()]

@app.post("/api/transfers")
def create_transfer(body: TransferCreate, db: Session = Depends(get_db), user: User = Depends(require_roles("ADMIN", "LOGISTICS_OFFICER", "BASE_COMMANDER"))):
    asset = db.get(Asset, body.asset_id)
    if not asset or not asset_allowed(user, asset): raise HTTPException(404, "Asset not found")
    if body.to_base_id == asset.base_id: raise HTTPException(400, "Destination must be different")
    if body.quantity <= 0 or body.quantity > asset.quantity: raise HTTPException(400, "Invalid quantity")
    old_base = asset.base_id
    asset.quantity -= body.quantity
    if asset.quantity == 0: asset.status = "TRANSFERRED"
    destination_asset = db.query(Asset).filter(Asset.base_id == body.to_base_id, Asset.equipment_type_id == asset.equipment_type_id, Asset.status == "AVAILABLE").first()
    if destination_asset: destination_asset.quantity += body.quantity
    else:
        destination_asset = Asset(asset_code=f"AST-{body.to_base_id}-{asset.equipment_type_id}-{int(datetime.utcnow().timestamp())}", equipment_type_id=asset.equipment_type_id, base_id=body.to_base_id, quantity=body.quantity, status="AVAILABLE")
        db.add(destination_asset); db.flush()
    t = Transfer(asset_id=asset.id, from_base_id=old_base, to_base_id=body.to_base_id, quantity=body.quantity, notes=body.notes)
    db.add(t); db.flush(); audit(db, user, "CREATE", "TRANSFER", t.id, f"from={old_base},to={body.to_base_id},quantity={body.quantity}"); db.commit()
    return {"message": "Transfer completed", "transfer_id": t.id}

@app.get("/api/transfers")
def list_transfers(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    q = db.query(Transfer).order_by(Transfer.transferred_at.desc())
    if user.role.name == "BASE_COMMANDER": q = q.filter((Transfer.from_base_id == user.base_id) | (Transfer.to_base_id == user.base_id))
    return [{"id": t.id, "asset_code": t.asset.asset_code, "from": t.from_base.name, "to": t.to_base.name, "quantity": t.quantity, "transferred_at": t.transferred_at, "notes": t.notes} for t in q.limit(100).all()]

@app.post("/api/assignments")
def create_assignment(body: AssignmentCreate, db: Session = Depends(get_db), user: User = Depends(require_roles("ADMIN", "BASE_COMMANDER"))):
    asset = db.get(Asset, body.asset_id)
    if not asset or not asset_allowed(user, asset): raise HTTPException(404, "Asset not found")
    if body.quantity <= 0 or body.quantity > asset.quantity: raise HTTPException(400, "Invalid quantity")
    asset.quantity -= body.quantity
    if asset.quantity == 0: asset.status = "ASSIGNED"
    item = Assignment(asset_id=asset.id, personnel_name=body.personnel_name, quantity=body.quantity)
    db.add(item); db.flush(); audit(db, user, "CREATE", "ASSIGNMENT", item.id, f"personnel={body.personnel_name},quantity={body.quantity}"); db.commit()
    return {"message": "Asset assigned", "assignment_id": item.id}

@app.get("/api/assignments")
def list_assignments(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    q = db.query(Assignment).join(Asset).order_by(Assignment.assigned_at.desc())
    if user.role.name == "BASE_COMMANDER": q = q.filter(Asset.base_id == user.base_id)
    return [{"id": x.id, "asset_code": x.asset.asset_code, "personnel_name": x.personnel_name, "quantity": x.quantity, "assigned_at": x.assigned_at, "returned_at": x.returned_at} for x in q.limit(100).all()]

@app.post("/api/expenditures")
def create_expenditure(body: ExpenditureCreate, db: Session = Depends(get_db), user: User = Depends(require_roles("ADMIN", "BASE_COMMANDER"))):
    asset = db.get(Asset, body.asset_id)
    if not asset or not asset_allowed(user, asset): raise HTTPException(404, "Asset not found")
    if body.quantity <= 0 or body.quantity > asset.quantity: raise HTTPException(400, "Invalid quantity")
    asset.quantity -= body.quantity
    if asset.quantity == 0: asset.status = "EXPENDED"
    item = Expenditure(asset_id=asset.id, quantity=body.quantity, reason=body.reason)
    db.add(item); db.flush(); audit(db, user, "CREATE", "EXPENDITURE", item.id, f"quantity={body.quantity},reason={body.reason}"); db.commit()
    return {"message": "Expenditure recorded", "expenditure_id": item.id}

@app.get("/api/audit-logs")
def audit_logs(db: Session = Depends(get_db), user: User = Depends(require_roles("ADMIN"))):
    rows = db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(200).all()
    return [{"id": x.id, "user": x.user.username, "action": x.action, "entity": x.entity, "entity_id": x.entity_id, "details": x.details, "created_at": x.created_at} for x in rows]
