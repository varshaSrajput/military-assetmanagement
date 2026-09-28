from app.database import Base, SessionLocal, engine
from app.models import Role, BaseLocation, User, EquipmentType
from app.security import hash_password

Base.metadata.create_all(bind=engine)
db = SessionLocal()
try:
    roles = ["ADMIN", "BASE_COMMANDER", "LOGISTICS_OFFICER"]
    role_map = {}
    for name in roles:
        r = db.query(Role).filter_by(name=name).first() or Role(name=name)
        db.add(r); db.flush(); role_map[name] = r
    bases = [("Alpha Base", "North Sector"), ("Bravo Base", "Central Sector"), ("Charlie Base", "South Sector")]
    base_map = {}
    for name, loc in bases:
        b = db.query(BaseLocation).filter_by(name=name).first() or BaseLocation(name=name, location=loc)
        db.add(b); db.flush(); base_map[name] = b
    types = [("Utility Vehicle", "Vehicle"), ("Communication Equipment", "Equipment"), ("Protective Equipment", "Equipment"), ("General Stores", "Supply")]
    for name, cat in types:
        if not db.query(EquipmentType).filter_by(name=name).first(): db.add(EquipmentType(name=name, category=cat))
    db.flush()
    users = [
        ("admin", "Admin User", "ADMIN", None, "Admin@123"),
        ("commander", "Alpha Base Commander", "BASE_COMMANDER", base_map["Alpha Base"].id, "Commander@123"),
        ("logistics", "Logistics Officer", "LOGISTICS_OFFICER", None, "Logistics@123"),
    ]
    for username, full_name, role, base_id, password in users:
        if not db.query(User).filter_by(username=username).first():
            db.add(User(username=username, full_name=full_name, role_id=role_map[role].id, base_id=base_id, password_hash=hash_password(password)))
    db.commit()
    print("Seed complete.")
    print("admin / Admin@123")
    print("commander / Commander@123")
    print("logistics / Logistics@123")
finally:
    db.close()
