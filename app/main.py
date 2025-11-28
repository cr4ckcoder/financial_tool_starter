from fastapi import FastAPI
from app.api import companies, works, accounts, templates, auth
from fastapi.middleware.cors import CORSMiddleware # <--- IMPORT THIS
from app.core.config import settings

app = FastAPI(title="Financial Statement Tool - Starter")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins (for development only)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# include routers
app.include_router(auth.router, prefix="/auth", tags=["auth"]) # <--- Register Auth
app.include_router(companies.router, prefix="/companies", tags=["companies"])
app.include_router(works.router, prefix="/works", tags=["works"])
app.include_router(accounts.router, prefix="/accounts", tags=["accounts"])
app.include_router(templates.router, prefix="/templates", tags=["templates"]) # <--- Register router
@app.get('/')
async def hello():
    return {"msg": "Financial Tool Starter - see /docs for API docs", "env": settings.APP_ENV}
