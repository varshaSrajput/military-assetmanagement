# Backend

The backend is written using FastAPI and SQLAlchemy.

## Main parts

- `app/main.py` - API routes and application setup
- `app/models.py` - database tables
- `app/schemas.py` - request/response models
- `app/security.py` - password and JWT helpers
- `app/dependencies.py` - logged-in user and role checks
- `app/database.py` - database connection
- `seed.py` - sample users, bases and equipment

## Run

```bash
pip install -r requirements.txt
python seed.py
uvicorn app.main:app --reload
```

FastAPI docs:

`http://localhost:8000/docs`
