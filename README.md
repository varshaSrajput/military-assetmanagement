# Military Asset Management System

This project is a simple web application for keeping track of equipment across different bases. It was built for the given assignment and covers the main flows mentioned in the requirements.

## Technology used

- React + Vite for the frontend
- Python + FastAPI for the backend
- MySQL for the database
- SQLAlchemy for database access
- JWT for login

## What the application does

- Login for three types of users: Admin, Base Commander and Logistics Officer
- Dashboard showing opening balance, closing balance, purchases, transfers and expenditure
- Filters for date and base
- Purchase entry and purchase history
- Asset transfers between bases
- Asset assignment to personnel
- Expenditure records
- Transfer and movement history
- Audit log for important actions
- Role based access in the backend

## Project folders

```text
backend/       FastAPI application
frontend/      React application
database/      MySQL schema and sample data
```

## Running the project

### 1. Set up MySQL

Create a database called `asset_management` and run:

```text
database/asset_management.sql
```

### 2. Start the backend

```bash
cd backend
python -m venv .venv
```

Windows:
```bash
.venv\\Scripts\\activate
```

macOS/Linux:
```bash
source .venv/bin/activate
```

Install the packages:

```bash
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and update the MySQL connection details.

Then run:

```bash
python seed.py
uvicorn app.main:app --reload
```

The API will run at `http://localhost:8000`.

### 3. Start the frontend

Open another terminal:

```bash
cd frontend
npm install
npm run dev
```

Open the local address shown by Vite, normally `http://localhost:5173`.

## Demo login details

```text
Admin
Username: admin
Password: Admin@123

Base Commander
Username: commander
Password: Commander@123

Logistics Officer
Username: logistics
Password: Logistics@123
```

These are only for local testing.

## Database design

The main tables are users, roles, bases, equipment types, assets, purchases, transfers, assignments, expenditures and audit logs.

The transaction tables are kept separately so that movements can be viewed later instead of only storing the current quantity.

## API documentation

After starting FastAPI, the API documentation is available at:

`http://localhost:8000/docs`
