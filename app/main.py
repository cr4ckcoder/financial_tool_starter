from fastapi import FastAPI
from app.api import companies, works, accounts
from app.core.config import settings

app = FastAPI(title="Financial Statement Tool - Starter")

# include routers
app.include_router(companies.router, prefix="/companies", tags=["companies"])
app.include_router(works.router, prefix="/works", tags=["works"])
app.include_router(accounts.router, prefix="/accounts", tags=["accounts"])

@app.get('/')
async def hello():
    return {"msg": "Financial Tool Starter - see /docs for API docs", "env": settings.APP_ENV}
