"""Backend IA — Granites MC CRM.

FastAPI backend pour les modules IA du CRM Granites MC :
- Coach de Vente IA (briefings pré-visite)
- Voix du Terrain (transcription + résumé IA)
"""

import os
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.config import get_settings
from app.models.schemas import HealthResponse
from app.routers import coach, voix, crm, admin, calendar
from app.services.odoo import get_odoo_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown events."""
    # Startup: test Odoo connection
    settings = get_settings()
    odoo = get_odoo_client()
    try:
        uid = await odoo.authenticate()
        print(f"✅ Odoo connecté (uid={uid})")
    except Exception as e:
        print(f"⚠️  Odoo non connecté: {e}")

    yield

    # Shutdown
    await odoo.close()
    print("🔒 Backend arrêté")


app = FastAPI(
    title="Granites MC — Backend IA",
    description=(
        "API backend pour les modules IA du CRM Granites MC. "
        "Coach de Vente, Voix du Terrain, connecteur Odoo."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

# CORS — permettre Odoo et localhost
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://granites-mc.odoo.com",
        "http://localhost:3000",
        "http://localhost:8000",
        "http://localhost:5173",
        "*",  # Prototype — à restreindre en production
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(coach.router)
app.include_router(voix.router)
app.include_router(crm.router)
app.include_router(admin.router)
app.include_router(calendar.router)


# Static interface files
STATIC_DIR = Path(__file__).parent / "static"
TAILADMIN_DIR = STATIC_DIR / "tailadmin"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# TailAdmin static assets (CSS, JS, images) — served at root level for TailAdmin's relative paths
if TAILADMIN_DIR.exists():
    app.mount("/app/src", StaticFiles(directory=str(TAILADMIN_DIR / "src")), name="tailadmin-src")


@app.get("/", include_in_schema=False)
async def root():
    return {"message": "Granites MC — Backend IA", "docs": "/docs"}


@app.get("/app/admin", include_in_schema=False)
async def serve_admin():
    """Interface Admin CRM."""
    return FileResponse(str(STATIC_DIR / "admin-v2.html"))


@app.get("/app/representant", include_in_schema=False)
async def serve_representant():
    """Interface Représentant."""
    return FileResponse(str(STATIC_DIR / "representant-v2.html"))


@app.get("/app/contacts", include_in_schema=False)
async def serve_contacts():
    """Annuaire / Contacts."""
    return FileResponse(str(STATIC_DIR / "contacts.html"))


# ── TailAdmin CRM pages ──────────────────────────────────────────────

@app.get("/app/crm", include_in_schema=False)
async def serve_crm_dashboard():
    """CRM Dashboard — TailAdmin."""
    return FileResponse(str(TAILADMIN_DIR / "index.html"))


@app.get("/app/crm/clients", include_in_schema=False)
async def serve_crm_clients():
    """Liste des clients — TailAdmin."""
    return FileResponse(str(TAILADMIN_DIR / "basic-tables.html"))


@app.get("/app/crm/client", include_in_schema=False)
async def serve_crm_client_profile():
    """Fiche client — TailAdmin."""
    return FileResponse(str(TAILADMIN_DIR / "profile.html"))


@app.get("/app/crm/calendrier", include_in_schema=False)
async def serve_crm_calendar():
    """Calendrier — TailAdmin."""
    return FileResponse(str(TAILADMIN_DIR / "calendar.html"))


@app.get("/app/crm/nouveau", include_in_schema=False)
async def serve_crm_new_client():
    """Formulaire nouveau client — TailAdmin."""
    return FileResponse(str(TAILADMIN_DIR / "form-elements.html"))


# TailAdmin static files (style.css, bundle.js, gmc-overrides.css, etc.)
@app.get("/app/{filename}", include_in_schema=False)
async def serve_tailadmin_asset(filename: str):
    """Serve TailAdmin static assets (CSS, JS, etc.)."""
    fpath = TAILADMIN_DIR / filename
    if fpath.exists() and fpath.is_file():
        return FileResponse(str(fpath))
    return {"error": "not found"}


# ── Legacy pages ──────────────────────────────────────────────────────

@app.get("/app/fiche-client", include_in_schema=False)
async def serve_fiche_client():
    """Fiche Client détaillée — vue Isabelle."""
    return FileResponse(str(STATIC_DIR / "fiche-client.html"))


@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health():
    """Vérifie l'état du backend et des connexions."""
    settings = get_settings()
    odoo = get_odoo_client()

    odoo_ok = False
    try:
        if odoo.uid:
            odoo_ok = True
        else:
            await odoo.authenticate()
            odoo_ok = True
    except Exception:
        pass

    return HealthResponse(
        status="ok",
        version="0.1.0",
        odoo_connected=odoo_ok,
        anthropic_configured=bool(settings.anthropic_api_key),
        deepgram_configured=bool(settings.deepgram_api_key),
    )
