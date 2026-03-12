"""Router Calendar — Endpoints pour le calendrier des représentants."""

from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from app.services.odoo import get_odoo_client

router = APIRouter(prefix="/api/calendar", tags=["Calendar"])


# ─── Schemas ───

class CalendarEventCreate(BaseModel):
    name: str
    start: str  # ISO format: "2026-03-15 09:00:00"
    stop: str   # ISO format: "2026-03-15 10:00:00"
    partner_id: Optional[int] = None  # Client lié
    user_id: Optional[int] = None  # Représentant assigné
    location: Optional[str] = None
    description: Optional[str] = None
    event_type: Optional[str] = "visit"  # visit, call, meeting, follow_up


class CalendarEventUpdate(BaseModel):
    name: Optional[str] = None
    start: Optional[str] = None
    stop: Optional[str] = None
    partner_id: Optional[int] = None
    location: Optional[str] = None
    description: Optional[str] = None


# ─── Helper ───

def _safe(val, default=""):
    """Sanitize Odoo False/None to default."""
    if val is False or val is None:
        return default
    if isinstance(val, (list, tuple)):
        return val[1] if len(val) > 1 else str(val[0]) if val else default
    return val


def _format_event(ev: dict) -> dict:
    """Format an Odoo calendar.event for API response."""
    partner_ids = ev.get("partner_ids", [])
    attendee_info = ev.get("attendee_ids", [])

    return {
        "id": ev["id"],
        "name": _safe(ev.get("name")),
        "start": _safe(ev.get("start")),
        "stop": _safe(ev.get("stop")),
        "allday": ev.get("allday", False),
        "duration": ev.get("duration", 0),
        "location": _safe(ev.get("location")),
        "description": _safe(ev.get("description")),
        "user_id": _safe(ev.get("user_id")),
        "partner_id": _safe(ev.get("partner_id")),
        "partner_ids": partner_ids,
        "state": _safe(ev.get("state")),
        "show_as": _safe(ev.get("show_as"), "busy"),
        "privacy": _safe(ev.get("privacy"), "public"),
        "categ_ids": ev.get("categ_ids", []),
        "activity_type": _safe(ev.get("res_model_id")),
    }


# ─── Endpoints ───

@router.get("/check")
async def check_calendar_module():
    """
    Vérifie si le module calendar est installé dans Odoo
    et retourne les infos de base.
    """
    odoo = get_odoo_client()

    try:
        # Check if calendar.event model exists
        fields = await odoo.fields_get("calendar.event", ["string", "type"])
        field_count = len(fields)

        # Count existing events
        event_count = await odoo.search_count("calendar.event", [])

        # Get calendar event types/categories
        try:
            categories = await odoo.search_read(
                "calendar.event.type", [], ["id", "name"], limit=50
            )
        except Exception:
            categories = []

        # Check if Google/Outlook sync is configured
        sync_info = {}
        try:
            sync_info["google_sync_available"] = "google_calendar_token" in fields
        except Exception:
            sync_info["google_sync_available"] = False

        return {
            "status": "ok",
            "calendar_module": "installed",
            "field_count": field_count,
            "event_count": event_count,
            "categories": categories,
            "sync_info": sync_info,
            "key_fields": [
                f for f in ["name", "start", "stop", "duration", "location",
                           "description", "partner_ids", "user_id", "allday",
                           "state", "show_as", "privacy", "categ_ids",
                           "partner_id", "res_model", "res_id",
                           "google_id", "microsoft_id"]
                if f in fields
            ],
        }
    except Exception as e:
        return {
            "status": "error",
            "calendar_module": "not_found_or_error",
            "detail": str(e),
        }


@router.get("/events")
async def list_events(
    start_date: Optional[str] = Query(None, description="Filter from date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Filter to date (YYYY-MM-DD)"),
    user_id: Optional[int] = Query(None, description="Filter by user/rep ID"),
    partner_id: Optional[int] = Query(None, description="Filter by client ID"),
    limit: int = Query(100, ge=1, le=500),
):
    """
    Retourne les événements du calendrier Odoo.
    Peut filtrer par date, représentant, ou client.
    """
    odoo = get_odoo_client()

    domain = []

    if start_date:
        domain.append(["start", ">=", f"{start_date} 00:00:00"])
    else:
        # Par défaut : événements des 30 derniers jours + 90 prochains jours
        default_start = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        domain.append(["start", ">=", f"{default_start} 00:00:00"])

    if end_date:
        domain.append(["stop", "<=", f"{end_date} 23:59:59"])

    if user_id:
        domain.append(["user_id", "=", user_id])

    if partner_id:
        domain.append(["partner_ids", "in", [partner_id]])

    fields = [
        "id", "name", "start", "stop", "allday", "duration",
        "location", "description", "user_id", "partner_id",
        "partner_ids", "state", "show_as", "privacy", "categ_ids",
    ]

    try:
        events = await odoo.search_read(
            "calendar.event", domain, fields,
            limit=limit, order="start asc"
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Erreur Odoo calendar: {str(e)}")

    formatted = [_format_event(ev) for ev in events]

    return {
        "count": len(formatted),
        "events": formatted,
    }


@router.get("/events/{event_id}")
async def get_event(event_id: int):
    """Retourne les détails d'un événement calendrier."""
    odoo = get_odoo_client()

    try:
        records = await odoo.read("calendar.event", [event_id], [
            "id", "name", "start", "stop", "allday", "duration",
            "location", "description", "user_id", "partner_id",
            "partner_ids", "attendee_ids", "state", "show_as",
            "privacy", "categ_ids", "recurrency", "interval",
        ])
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Erreur Odoo: {str(e)}")

    if not records:
        raise HTTPException(status_code=404, detail=f"Événement {event_id} non trouvé")

    return _format_event(records[0])


@router.post("/events")
async def create_event(data: CalendarEventCreate):
    """
    Crée un événement calendrier dans Odoo.
    Utilisé pour planifier des visites représentant.
    """
    odoo = get_odoo_client()

    values = {
        "name": data.name,
        "start": data.start,
        "stop": data.stop,
    }

    if data.partner_id:
        values["partner_ids"] = [(4, data.partner_id)]  # Link partner

    if data.user_id:
        values["user_id"] = data.user_id

    if data.location:
        values["location"] = data.location

    if data.description:
        values["description"] = data.description

    try:
        event_id = await odoo.create("calendar.event", values)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Erreur Odoo: {str(e)}")

    return {"status": "ok", "event_id": event_id, "name": data.name}


@router.put("/events/{event_id}")
async def update_event(event_id: int, data: CalendarEventUpdate):
    """Met à jour un événement calendrier existant."""
    odoo = get_odoo_client()

    update_vals = {}
    for field, value in data.model_dump(exclude_unset=True).items():
        if value is not None:
            if field == "partner_id" and value:
                update_vals["partner_ids"] = [(4, value)]
            else:
                update_vals[field] = value

    if not update_vals:
        raise HTTPException(status_code=400, detail="Aucun champ à mettre à jour")

    try:
        await odoo.write("calendar.event", [event_id], update_vals)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Erreur Odoo: {str(e)}")

    return {"status": "ok", "event_id": event_id, "updated_fields": list(update_vals.keys())}


@router.delete("/events/{event_id}")
async def delete_event(event_id: int):
    """Supprime un événement calendrier."""
    odoo = get_odoo_client()

    try:
        await odoo._call_kw("calendar.event", "unlink", [[event_id]])
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Erreur Odoo: {str(e)}")

    return {"status": "ok", "deleted_event_id": event_id}


@router.get("/users")
async def list_calendar_users():
    """
    Retourne les utilisateurs Odoo (représentants) qui peuvent avoir des événements.
    Utile pour le filtre par représentant dans l'interface.
    """
    odoo = get_odoo_client()

    try:
        users = await odoo.search_read(
            "res.users",
            [["active", "=", True], ["share", "=", False]],
            ["id", "name", "email", "login"],
            order="name asc",
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Erreur Odoo: {str(e)}")

    return {
        "count": len(users),
        "users": [
            {
                "id": u["id"],
                "name": _safe(u.get("name")),
                "email": _safe(u.get("email")),
            }
            for u in users
        ],
    }


@router.get("/sync-status")
async def get_sync_status():
    """
    Vérifie l'état de la synchronisation Google/Outlook Calendar.
    """
    odoo = get_odoo_client()

    try:
        fields = await odoo.fields_get("calendar.event", ["string", "type"])

        result = {
            "google_sync": {
                "available": "google_id" in fields,
                "field_exists": "google_id" in fields,
            },
            "microsoft_sync": {
                "available": "microsoft_id" in fields or "microsoft_recurrence_master_id" in fields,
                "field_exists": "microsoft_id" in fields,
            },
        }

        # Check if any events have google/microsoft IDs (meaning sync is active)
        if result["google_sync"]["available"]:
            google_count = await odoo.search_count(
                "calendar.event", [["google_id", "!=", False]]
            )
            result["google_sync"]["synced_events"] = google_count

        if result["microsoft_sync"]["available"]:
            ms_count = await odoo.search_count(
                "calendar.event", [["microsoft_id", "!=", False]]
            )
            result["microsoft_sync"]["synced_events"] = ms_count

        return result

    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Erreur: {str(e)}")


@router.post("/seed-demo")
async def seed_demo_events():
    """
    Génère ~11 événements fictifs pour démonstration.
    Utilisé pour le prototype — à retirer en production.
    """
    odoo = get_odoo_client()

    demo_events = [
        {
            "name": "Visite Cuisifab 3ri — suivi soumission comptoirs",
            "start": "2026-03-12 09:00:00",
            "stop": "2026-03-12 10:30:00",
            "partner_ids": [(4, 423)],
            "location": "5075 Boul. des Forges, Trois-Rivières",
            "description": "Suivi de la soumission envoyée le 5 mars. Vérifier intérêt pour gamme quartz premium.",
        },
        {
            "name": "Appel Avivia Cuisines — relance échantillons",
            "start": "2026-03-12 14:00:00",
            "stop": "2026-03-12 14:30:00",
            "location": "Téléphone",
            "description": "Relancer suite à l'envoi d'échantillons de granit.",
        },
        {
            "name": "Visite Cuisi-Meuble S.M. — présentation nouveautés",
            "start": "2026-03-13 10:00:00",
            "stop": "2026-03-13 11:30:00",
            "partner_ids": [(4, 561)],
            "location": "Tingwick",
            "description": "Présentation des nouvelles collections 2026.",
        },
        {
            "name": "Réunion équipe — bilan mensuel mars",
            "start": "2026-03-13 15:00:00",
            "stop": "2026-03-13 16:30:00",
            "location": "Bureau Granites MC, Trois-Rivières",
            "description": "Bilan des ventes mars, objectifs Q2.",
        },
        {
            "name": "Visite Armoires Distinction — démo logiciel",
            "start": "2026-03-16 09:30:00",
            "stop": "2026-03-16 11:00:00",
            "partner_ids": [(4, 424)],
            "location": "Sherbrooke",
            "description": "Démonstration du nouveau configurateur en ligne.",
        },
        {
            "name": "Appel Armoires B.M.S. — suivi commande",
            "start": "2026-03-16 13:30:00",
            "stop": "2026-03-16 14:00:00",
            "partner_ids": [(4, 564)],
            "location": "Téléphone",
            "description": "Confirmer réception commande #2847.",
        },
        {
            "name": "Visite Cuisines M.R.S. / Cuisimax — négociation annuelle",
            "start": "2026-03-17 10:00:00",
            "stop": "2026-03-17 12:00:00",
            "partner_ids": [(4, 562)],
            "location": "Victoriaville",
            "description": "Négociation du contrat annuel 2026-2027.",
        },
        {
            "name": "Suivi Armoires N.S. — qualité livraison",
            "start": "2026-03-17 14:00:00",
            "stop": "2026-03-17 15:00:00",
            "partner_ids": [(4, 563)],
            "location": "Téléphone",
            "description": "Suivi qualité suite à dernière livraison.",
        },
        {
            "name": "Visite Groupe BMR — prospection nouveau compte",
            "start": "2026-03-18 09:00:00",
            "stop": "2026-03-18 10:30:00",
            "location": "Boucherville",
            "description": "Première rencontre avec directeur achats.",
        },
        {
            "name": "Visite Armoire B.M. — échantillons nouveaux finis",
            "start": "2026-03-19 10:00:00",
            "stop": "2026-03-19 11:30:00",
            "partner_ids": [(4, 565)],
            "location": "Drummondville",
            "description": "Nouveaux échantillons finis mat et texturés.",
        },
        {
            "name": "Appel SMA Solutions — planification visite Q2",
            "start": "2026-03-19 15:00:00",
            "stop": "2026-03-19 15:30:00",
            "location": "Téléphone",
            "description": "Planifier visites Q2, confirmer objectifs volume.",
        },
    ]

    created = []
    errors = []

    for ev in demo_events:
        try:
            event_id = await odoo.create("calendar.event", ev)
            created.append({"id": event_id, "name": ev["name"]})
        except Exception as e:
            errors.append({"name": ev["name"], "error": str(e)})

    return {
        "status": "ok",
        "created_count": len(created),
        "error_count": len(errors),
        "created": created,
        "errors": errors,
    }
