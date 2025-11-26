# LibraDB - Library Management System

Flask + SQLite library manager with a single login/registration screen, role-aware portals, librarian approvals, and sample seed data.

## Windows + SQLite quick start

### First-time setup (Windows 10/11 + PowerShell, Python 3.11+)
```powershell
git clone https://github.com/your-org/LibraDB.git
cd "LibraDB"  # or your folder name
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt

# optional: explicitly set SQLite path (default is library.db in project root)
$env:DATABASE_URL = "sqlite:///library.db"

# create tables (migrations if present, otherwise create_all on first run)
python -m flask --app app db upgrade

# optional demo data (idempotent)
python -m flask --app app seed

# start the app
python -m flask --app app run --debug
```

### Run again (after initial setup)
```powershell
cd "LibraDB"
.\.venv\Scripts\activate
python -m flask --app app run --debug
```

## Accounts and flow

- **Librarian demo:** `librarian@example.com / admin123`
- **Member demo:** `alice@example.com / password123`
- New users register as members only from the login page; a librarian must approve their account before they can sign in.
- Member booking requests also require librarian approval before they count against available copies.

## Project structure

```
├── app.py                # Flask entry point
├── library_app
│   ├── __init__.py       # App factory and extensions
│   ├── config.py         # Settings (secret key, DB URI)
│   ├── models.py         # SQLAlchemy models
│   ├── routes.py         # Views / controllers
│   ├── seed.py           # Demo data helper
│   ├── templates         # Jinja templates for UI
│   └── static            # CSS assets
├── requirements.txt
└── README.md
```

## Deploying to Vercel

The repository is wired for Vercel's Python runtime via the included `vercel.json`. To deploy:

1. **Provision a persistent database.** Vercel serverless functions have ephemeral storage, so use a hosted database such as Neon, Supabase, PlanetScale, or Railway. Capture its connection string (e.g., `postgresql://...` or `mysql://...`).
2. **Set required environment variables** in the Vercel dashboard (or via `vercel env`):
   - `SECRET_KEY`: any random string for Flask sessions.
   - `DATABASE_URL`: the connection string for your remote database.
3. **Install dependencies & build:**
   - If you're testing locally with the Vercel CLI, run `npm i -g vercel` and `vercel dev` to spin up the serverless function locally.
4. **Deploy:**
   - Run `vercel --prod` from the project root or connect the repository in the Vercel dashboard and trigger a deployment.

The `@vercel/python` builder targets `app.py` and routes all requests to the Flask application, so no additional server entrypoint is needed.
