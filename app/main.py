# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import all routers
from app.api import (
    auth, 
    companies, 
    works, 
    accounts, 
    templates, 
    report_config, 
    signatories,
    settings,     # <--- Phase 4: Firm Settings
    compliance    # <--- Phase 4: Document Generation (THIS WAS LIKELY MISSING)
)
from app.core.config import settings as app_settings

app = FastAPI(title="Finstat - Financial Tool Pro")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Register Routers ---
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(companies.router, prefix="/companies", tags=["companies"])
app.include_router(signatories.router, prefix="/signatories", tags=["signatories"])
app.include_router(works.router, prefix="/works", tags=["works"])
app.include_router(accounts.router, prefix="/accounts", tags=["accounts"])
app.include_router(templates.router, prefix="/templates", tags=["templates"])
app.include_router(report_config.router, prefix="/reports", tags=["reports"])

# Phase 4 New Routers
app.include_router(settings.router, prefix="/settings", tags=["settings"])
app.include_router(compliance.router, prefix="/compliance", tags=["compliance"]) # <--- CRITICAL FIX

@app.get('/')
async def hello():
    return {"msg": "Finstat API is running", "env": app_settings.APP_ENV}