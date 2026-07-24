from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.core.database import Base, engine
from app.repositories import models
from app.api import products

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Catalog Enrichment API")
app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.include_router(products.router)

@app.get("/health")
def health():
    return {"status": "ok"}