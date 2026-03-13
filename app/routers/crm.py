"""Router CRM — Endpoints pour les données clients, pipeline, et statistiques."""

from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from app.models.schemas import (
    ClientListResponse,
    ClientDetailResponse,
    PipelineResponse,
    StatsResponse,
    TerritoryResponse,
    RepresentativeResponse,
)
from app.services.odoo import get_odoo_client

router = APIRouter(prefix="/api/crm", tags=["CRM"])

# ─── Stage name mapping: Odoo stage names → frontend stage names ───
STAGE_MAP = {
    "New": "Soumission",
    "Nouveau": "Soumission",
    "Qualification": "En attente",
    "Qualified": "En attente",
    "Proposition": "En attente",
    "Negotiation": "En cours",
    "Négociation": "En cours",
    "Won": "Signé",
    "Gagné": "Signé",
    "Lost": "Perdu",
    "Perdu": "Perdu",
}


def _s(val, default=""):
    """Sanitize Odoo field value: convert False/None/list to default string."""
    if val is False or val is None:
        return default
    if isinstance(val, (list, tuple)):
        return ", ".join(str(v) for v in val) if val else default
    return val


def _i(val, default=0):
    """Sanitize Odoo integer field: convert False/None to default int."""
    if val is False or val is None:
        return default
    return val


@router.get("/clients", response_model=ClientListResponse)
async def list_clients(
    territoire_id: Optional[int] = Query(None, description="Filter by territory ID"),
    score: Optional[str] = Query(None, description="Filter by score (A, B, C)"),
    search: Optional[str] = Query(None, description="Search by name, city, phone, email"),
    user_id: Optional[int] = Query(None, description="Filter by salesperson/rep user ID"),
    limit: int = Query(500, ge=1, le=5000, description="Max results"),
):
    """
    Retourne la liste des clients (contacts de type entreprise).

    Supporte les filtres par territoire, score client, recherche textuelle,
    et par représentant (user_id → filtre par leads assignés au rep).
    Format flat array compatible AG Grid.
    """
    odoo = get_odoo_client()

    # If user_id is provided, first find partner IDs that have leads assigned to this user
    partner_ids_for_user = None
    if user_id:
        try:
            user_leads = await odoo.search_read(
                "crm.lead",
                [["user_id", "=", user_id]],
                ["partner_id"],
                limit=1000,
            )
            partner_ids_for_user = list(set(
                l["partner_id"][0] if isinstance(l.get("partner_id"), (list, tuple)) else l.get("partner_id")
                for l in user_leads
                if l.get("partner_id")
            ))
        except Exception:
            partner_ids_for_user = None

    domain = [["is_company", "=", True]]

    if partner_ids_for_user is not None:
        if partner_ids_for_user:
            domain.append(["id", "in", partner_ids_for_user])
        else:
            # No leads for this user, return empty
            return ClientListResponse(count=0, clients=[])

    if territoire_id:
        domain.append(["x_territoire", "=", territoire_id])
    if score:
        domain.append(["x_score_client", "=", score])
    if search:
        search_domain = [
            "&",
            ["is_company", "=", True],
            "|", "|", "|",
            ["name", "ilike", search],
            ["city", "ilike", search],
            ["phone", "ilike", search],
            ["email", "ilike", search],
        ]
        if partner_ids_for_user:
            # Combine search with user filter
            domain = ["&", ["id", "in", partner_ids_for_user]] + search_domain
        else:
            domain = search_domain

    # Try with custom fields first, fallback to basic fields
    basic_fields = ["id", "name", "city", "phone", "email", "website", "street", "zip"]
    custom_fields = [
        "x_territoire", "x_score_client", "x_notes_terrain",
        "x_competiteurs", "x_marques_interet", "x_type_client",
        "x_facebook", "x_instagram", "x_linkedin", "x_google_maps",
        "x_description", "x_year_founded", "x_employees_estimate",
        "x_revenue_estimate", "x_req_number", "x_brands",
        "x_specialties", "x_hours",
    ]

    try:
        clients = await odoo.search_read(
            "res.partner", domain, basic_fields + custom_fields,
            limit=limit, order="name asc",
        )
    except Exception:
        # Fallback: custom fields might not exist
        try:
            clients = await odoo.search_read(
                "res.partner", domain, basic_fields,
                limit=limit, order="name asc",
            )
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Erreur Odoo: {str(e)}")

    # Transform data for frontend
    response_clients = []
    for c in clients:
        terr = c.get("x_territoire")
        terr_name = terr[1] if isinstance(terr, (list, tuple)) else str(terr or "") if terr else ""
        terr_val = terr if isinstance(terr, (list, tuple)) else None

        response_clients.append({
            "id": c["id"],
            "name": c.get("name", ""),
            "nom_legal": c.get("name", ""),
            "territoire": terr_name,
            "x_territoire": terr_val,
            "x_score_client": _s(c.get("x_score_client")),
            "city": _s(c.get("city")),
            "phone": _s(c.get("phone")),
            "email": _s(c.get("email")),
            "website": _s(c.get("website")),
            "street": _s(c.get("street")),
            "zip": _s(c.get("zip")),
            "x_notes_terrain": _s(c.get("x_notes_terrain")),
            "x_competiteurs": _s(c.get("x_competiteurs")),
            "x_marques_interet": _s(c.get("x_marques_interet")),
            "x_date_derniere_visite": None,
            "x_nb_visites": 0,
            "lead_count": 0,
            "x_type_client": _s(c.get("x_type_client")),
            "x_facebook": _s(c.get("x_facebook")),
            "x_instagram": _s(c.get("x_instagram")),
            "x_linkedin": _s(c.get("x_linkedin")),
            "x_google_maps": _s(c.get("x_google_maps")),
            "x_description": _s(c.get("x_description")),
            "x_year_founded": _s(c.get("x_year_founded")),
            "x_employees_estimate": _s(c.get("x_employees_estimate")),
            "x_revenue_estimate": _s(c.get("x_revenue_estimate")),
            "x_req_number": _s(c.get("x_req_number")),
            "x_brands": _s(c.get("x_brands")),
            "x_specialties": _s(c.get("x_specialties")),
            "x_hours": _s(c.get("x_hours")),
        })

    return ClientListResponse(
        count=len(response_clients),
        clients=response_clients,
    )


@router.get("/clients/{partner_id}", response_model=ClientDetailResponse)
async def get_client_detail(partner_id: int):
    """
    Retourne les détails complets d'un client.

    Inclut les informations de base, les contacts enfants, les leads CRM,
    et les activités récentes.
    """
    odoo = get_odoo_client()

    try:
        partner = await odoo.get_partner(partner_id)
    except ValueError:
        raise HTTPException(status_code=404, detail=f"Client {partner_id} non trouvé")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Erreur Odoo get_partner: {str(e)}")

    # Get related contacts (child addresses)
    try:
        child_contacts = await odoo.search_read(
            "res.partner",
            [["parent_id", "=", partner_id], ["is_company", "=", False]],
            ["id", "name", "email", "phone", "function"],
            order="name asc",
        )
    except Exception:
        child_contacts = []

    # Get related leads
    try:
        leads = await odoo.get_partner_leads(partner_id)
    except Exception:
        leads = []

    # Get recent activities
    try:
        activities = await odoo.get_partner_activities(partner_id)
    except Exception:
        activities = []

    # Format territory
    terr = partner.get("x_territoire")
    terr_name = terr[1] if isinstance(terr, (list, tuple)) else str(terr or "")

    try:
        return ClientDetailResponse(
            id=partner["id"],
            name=_s(partner.get("name"), ""),
            is_company=bool(partner.get("is_company", True)),
            territoire=terr_name,
            x_score_client=_s(partner.get("x_score_client")),
            city=_s(partner.get("city")),
            phone=_s(partner.get("phone")),
            email=_s(partner.get("email")),
            website=_s(partner.get("website")),
            street=_s(partner.get("street")),
            zip=_s(partner.get("zip")),
            state_id=partner.get("state_id") if partner.get("state_id") else None,
            x_notes_terrain=_s(partner.get("x_notes_terrain")),
            x_competiteurs=_s(partner.get("x_competiteurs")),
            x_marques_interet=_s(partner.get("x_marques_interet")),
            x_date_derniere_visite=_s(partner.get("x_date_derniere_visite"), None),
            x_nb_visites=_i(partner.get("x_nb_visites")),
            x_type_client=_s(partner.get("x_type_client")),
            x_echantillons_notes=_s(partner.get("x_echantillons_notes")),
            x_facebook=_s(partner.get("x_facebook")),
            x_instagram=_s(partner.get("x_instagram")),
            x_linkedin=_s(partner.get("x_linkedin")),
            x_google_maps=_s(partner.get("x_google_maps")),
            x_description=_s(partner.get("x_description")),
            x_year_founded=_s(partner.get("x_year_founded")),
            x_employees_estimate=_s(partner.get("x_employees_estimate")),
            x_revenue_estimate=_s(partner.get("x_revenue_estimate")),
            x_req_number=_s(partner.get("x_req_number")),
            x_brands=_s(partner.get("x_brands")),
            x_specialties=_s(partner.get("x_specialties")),
            x_hours=_s(partner.get("x_hours")),
            # Isabelle fields
            x_freq_visite=_s(partner.get("x_freq_visite")),
            x_date_premiere_visite=_s(partner.get("x_date_premiere_visite")),
            x_meilleure_annee=_s(partner.get("x_meilleure_annee")),
            x_ventes_2019=float(partner.get("x_ventes_2019") or 0),
            x_ventes_2020=float(partner.get("x_ventes_2020") or 0),
            x_ventes_2021=float(partner.get("x_ventes_2021") or 0),
            x_ventes_2022=float(partner.get("x_ventes_2022") or 0),
            x_ventes_2023=float(partner.get("x_ventes_2023") or 0),
            x_ventes_total=float(partner.get("x_ventes_total") or 0),
            x_contact_principal=_s(partner.get("x_contact_principal")),
            x_contact_secondaire=_s(partner.get("x_contact_secondaire")),
            x_echantillons_livres=_s(partner.get("x_echantillons_livres")),
            x_historique_visites=_s(partner.get("x_historique_visites")),
            x_bon_soumission=_s(partner.get("x_bon_soumission")),
            x_provenance=_s(partner.get("x_provenance")),
            x_salle_montre=_s(partner.get("x_salle_montre")),
            x_notes_isabelle=_s(partner.get("x_notes_isabelle")),
            tag_ids=partner.get("category_id", []) if isinstance(partner.get("category_id"), list) else [],
            child_contacts=child_contacts,
            leads=leads,
            activities=activities,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur construction réponse pour {partner_id}: {type(e).__name__}: {str(e)}"
        )


@router.get("/pipeline", response_model=dict)
async def get_pipeline(
    limit: int = Query(500, ge=1, le=5000),
    user_id: Optional[int] = Query(None, description="Filter by assigned user/rep ID"),
):
    """
    Retourne les crm.lead (opportunités) du pipeline.

    Supporte le filtre par user_id pour voir le pipeline d'un rep spécifique.
    """
    odoo = get_odoo_client()

    domain = []
    if user_id:
        domain.append(["user_id", "=", user_id])

    fields = [
        "id",
        "name",
        "stage_id",
        "partner_id",
        "expected_revenue",
        "probability",
        "date_deadline",
        "create_date",
        "user_id",
        "description",
        "tag_ids",
    ]

    try:
        leads = await odoo.search_read(
            "crm.lead",
            domain,
            fields,
            limit=limit,
            order="create_date desc",
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Erreur Odoo: {str(e)}")

    # Transform data
    response_leads = []
    for lead in leads:
        partner = lead.get("partner_id")
        partner_name = partner[1] if isinstance(partner, (list, tuple)) else ""

        stage = lead.get("stage_id")
        stage_name = stage[1] if isinstance(stage, (list, tuple)) else ""

        user = lead.get("user_id")
        user_name = user[1] if isinstance(user, (list, tuple)) else ""

        response_leads.append({
            "id": lead["id"],
            "name": lead.get("name", ""),
            "stage_id": lead.get("stage_id"),
            "stage_name": stage_name,
            "partner_id": lead.get("partner_id"),
            "partner_name": partner_name,
            "expected_revenue": lead.get("expected_revenue", 0),
            "probability": lead.get("probability", 0),
            "date_deadline": lead.get("date_deadline"),
            "create_date": lead.get("create_date"),
            "user_id": lead.get("user_id"),
            "user_name": user_name,
            "description": lead.get("description", ""),
            "tag_ids": lead.get("tag_ids", []),
        })

    return {
        "count": len(response_leads),
        "leads": response_leads,
    }


@router.get("/stats", response_model=StatsResponse)
async def get_stats(
    user_id: Optional[int] = Query(None, description="Filter stats by user/rep ID"),
):
    """
    Retourne les statistiques du CRM pour le dashboard.

    Total clients, répartition par score, par territoire,
    statistiques du pipeline, et dernière activité.
    Supporte le filtre par user_id pour stats personnalisées.
    """
    odoo = get_odoo_client()

    try:
        # Total clients
        total_clients = await odoo.search_count(
            "res.partner",
            [["is_company", "=", True]],
        )

        # Clients by score (with fallback if custom field doesn't exist)
        try:
            score_a = await odoo.search_count(
                "res.partner",
                [["is_company", "=", True], ["x_score_client", "=", "A"]],
            )
            score_b = await odoo.search_count(
                "res.partner",
                [["is_company", "=", True], ["x_score_client", "=", "B"]],
            )
            score_c = await odoo.search_count(
                "res.partner",
                [["is_company", "=", True], ["x_score_client", "=", "C"]],
            )
        except Exception:
            score_a = score_b = score_c = 0

        # Pipeline stats
        lead_domain = [["user_id", "=", user_id]] if user_id else []
        total_leads = await odoo.search_count("crm.lead", lead_domain)

        # Get leads grouped by stage with total revenue
        all_leads = await odoo.search_read(
            "crm.lead",
            lead_domain,
            ["stage_id", "expected_revenue", "probability"],
            limit=1000,
        )

        pipeline_revenue = 0
        stage_stats = {}
        for lead in all_leads:
            stage = lead.get("stage_id")
            stage_id = stage[0] if isinstance(stage, (list, tuple)) else stage
            stage_name = stage[1] if isinstance(stage, (list, tuple)) else str(stage)

            if stage_name not in stage_stats:
                stage_stats[stage_name] = {"count": 0, "revenue": 0}

            stage_stats[stage_name]["count"] += 1
            revenue = lead.get("expected_revenue", 0)
            stage_stats[stage_name]["revenue"] += revenue
            pipeline_revenue += revenue

        # Recent activities (may fail if no activities exist)
        try:
            recent_activities = await odoo.search_read(
                "mail.activity",
                [["res_model", "=", "res.partner"]],
                ["res_id", "summary", "date_deadline", "state"],
                order="create_date desc",
                limit=10,
            )
        except Exception:
            recent_activities = []

    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Erreur Odoo: {str(e)}")

    return StatsResponse(
        total_clients=total_clients,
        clients_by_score={
            "A": score_a,
            "B": score_b,
            "C": score_c,
        },
        total_leads=total_leads,
        pipeline_revenue=pipeline_revenue,
        pipeline_by_stage=stage_stats,
        recent_activities_count=len(recent_activities),
    )


@router.get("/territories", response_model=dict)
async def get_territories():
    """
    Retourne la liste des territoires avec le nombre de clients par territoire.
    """
    odoo = get_odoo_client()

    try:
        teams = await odoo.search_read(
            "crm.team",
            [],
            ["id", "name"],
            order="name asc",
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Erreur Odoo: {str(e)}")

    # Get client count per territory (x_territoire may not exist)
    territories = []
    for team in teams:
        try:
            count = await odoo.search_count(
                "res.partner",
                [["is_company", "=", True], ["x_territoire", "=", team["id"]]],
            )
        except Exception:
            count = 0
        territories.append({
            "id": team["id"],
            "name": team.get("name", ""),
            "client_count": count,
        })

    return {
        "count": len(territories),
        "territories": territories,
    }


@router.get("/reps", response_model=dict)
async def get_representatives():
    """
    Retourne la liste des représentants/vendeurs avec statistiques.
    """
    odoo = get_odoo_client()

    try:
        users = await odoo.search_read(
            "res.users",
            [["active", "=", True]],
            ["id", "name", "email", "phone"],
            order="name asc",
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Erreur Odoo: {str(e)}")

    representatives = []
    for user in users:
        # Get team(s) for this user
        try:
            teams_list = await odoo.search_read(
                "crm.team",
                [["member_ids", "in", [user["id"]]]],
                ["id", "name"],
            )
        except Exception:
            teams_list = []

        # Get lead count for this user
        try:
            lead_count = await odoo.search_count(
                "crm.lead",
                [["user_id", "=", user["id"]]],
            )
        except Exception:
            lead_count = 0

        # Get pipeline revenue
        try:
            user_leads = await odoo.search_read(
                "crm.lead",
                [["user_id", "=", user["id"]]],
                ["expected_revenue"],
            )
            pipeline_revenue = sum(l.get("expected_revenue", 0) or 0 for l in user_leads)
        except Exception:
            pipeline_revenue = 0

        team_names = [t["name"] for t in teams_list] if teams_list else []

        representatives.append({
            "id": user["id"],
            "name": user.get("name", "") or "",
            "email": user.get("email", "") or "",
            "phone": user.get("phone", "") or "",
            "teams": team_names,
            "lead_count": lead_count,
            "pipeline_revenue": pipeline_revenue,
        })

    return {
        "count": len(representatives),
        "reps": representatives,
    }


@router.post("/auth/login", response_model=dict)
async def login(email: str = Query(..., description="User email for login")):
    """
    Authentification simple par email.

    Recherche un utilisateur Odoo par email et retourne son profil + rôle.
    Pour le prototype — pas de mot de passe, juste identification par email.
    """
    odoo = get_odoo_client()

    try:
        users = await odoo.search_read(
            "res.users",
            [["email", "=", email], ["active", "=", True]],
            ["id", "name", "email", "phone", "login"],
            limit=1,
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Erreur Odoo: {str(e)}")

    if not users:
        raise HTTPException(status_code=404, detail=f"Aucun utilisateur trouvé avec l'email: {email}")

    user = users[0]
    user_id = user["id"]

    # Determine role (admin vs rep)
    # Simple role detection: admin emails, otherwise rep
    admin_emails = ["pgirardin@saiphia.ca", "nathalie.beaulac@granitesmc.com"]
    is_admin = (user.get("email") or "").lower() in admin_emails

    # Get team membership
    try:
        teams = await odoo.search_read(
            "crm.team",
            [["member_ids", "in", [user_id]]],
            ["id", "name"],
        )
    except Exception:
        teams = []

    # Get assigned clients count
    try:
        # For now, all company partners — later filter by salesperson_id or territory
        client_count = await odoo.search_count(
            "res.partner",
            [["is_company", "=", True]],
        )
    except Exception:
        client_count = 0

    # Get pipeline stats for this user
    try:
        user_leads = await odoo.search_read(
            "crm.lead",
            [["user_id", "=", user_id]],
            ["expected_revenue"],
        )
        pipeline_revenue = sum(l.get("expected_revenue", 0) or 0 for l in user_leads)
        lead_count = len(user_leads)
    except Exception:
        pipeline_revenue = 0
        lead_count = 0

    return {
        "status": "ok",
        "user": {
            "id": user_id,
            "name": user.get("name", ""),
            "email": user.get("email", ""),
            "phone": _s(user.get("phone")),
            "role": "admin" if is_admin else "rep",
            "teams": [{"id": t["id"], "name": t["name"]} for t in teams],
        },
        "stats": {
            "client_count": client_count,
            "lead_count": lead_count,
            "pipeline_revenue": pipeline_revenue,
        },
    }


@router.get("/auth/users", response_model=dict)
async def list_auth_users():
    """
    Liste les utilisateurs disponibles pour le login (prototype).

    Retourne un dropdown-ready des users Odoo actifs.
    """
    odoo = get_odoo_client()

    try:
        users = await odoo.search_read(
            "res.users",
            [["active", "=", True]],
            ["id", "name", "email"],
            order="name asc",
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Erreur Odoo: {str(e)}")

    # Exclude system/admin users from login list (prototype)
    excluded_emails = {"pgirardin@saiphia.ca", "alexandre.bouffard@granitesmc.com"}
    filtered = [u for u in users if (_s(u.get("email"))).lower() not in excluded_emails]

    return {
        "count": len(filtered),
        "users": [
            {
                "id": u["id"],
                "name": u.get("name", ""),
                "email": _s(u.get("email")),
            }
            for u in filtered
        ],
    }


# ─── NEW: All-in-one dashboard endpoint ───

@router.get("/dashboard", response_model=dict)
async def get_dashboard(
    user_id: Optional[int] = Query(None, description="User/rep ID for personalized dashboard"),
):
    """
    Endpoint all-in-one pour le dashboard d'un représentant.

    Retourne en un seul appel: clients, pipeline, stats, activités récentes.
    Si user_id est fourni, filtre tout par ce représentant.
    """
    odoo = get_odoo_client()

    result = {
        "mode": "live",
        "clients": [],
        "pipeline": [],
        "stats": {},
        "activities": [],
        "timeline": [],
    }

    # ── 1. Get clients and leads ──
    try:
        lead_fields = ["partner_id", "expected_revenue", "probability", "stage_id",
             "name", "create_date", "date_deadline", "user_id", "description", "tag_ids"]

        # Try user-filtered first
        user_leads = []
        if user_id:
            user_leads = await odoo.search_read(
                "crm.lead", [["user_id", "=", user_id]],
                lead_fields, limit=500, order="create_date desc",
            )

        # Fallback: if no leads for this user, load ALL leads
        if not user_leads:
            user_leads = await odoo.search_read(
                "crm.lead", [],
                lead_fields, limit=500, order="create_date desc",
            )

        # Extract unique partner IDs from leads
        partner_ids_from_leads = list(set(
            l["partner_id"][0] if isinstance(l.get("partner_id"), (list, tuple)) else l.get("partner_id")
            for l in user_leads if l.get("partner_id")
        ))

        # Get ALL company partners — always show all clients in dashboard
        basic_fields = ["id", "name", "city", "phone", "email", "website", "street", "zip",
                        "country_id", "category_id"]
        custom_fields = [
            "x_territoire", "x_score_client", "x_notes_terrain",
            "x_competiteurs", "x_marques_interet", "x_type_client",
            "x_facebook", "x_instagram", "x_linkedin", "x_google_maps",
            "x_description", "x_year_founded", "x_employees_estimate",
            "x_revenue_estimate", "x_req_number", "x_brands",
            "x_specialties", "x_hours",
        ]
        try:
            clients = await odoo.search_read(
                "res.partner",
                [["is_company", "=", True]],
                basic_fields + custom_fields,
                limit=500, order="name asc",
            )
        except Exception:
            try:
                clients = await odoo.search_read(
                    "res.partner",
                    [["is_company", "=", True]],
                    basic_fields,
                    limit=500, order="name asc",
                )
            except Exception:
                clients = []

        # If still no company partners, try ALL partners
        if not clients:
            try:
                clients = await odoo.search_read(
                    "res.partner",
                    [["active", "=", True]],
                    basic_fields,
                    limit=200, order="name asc",
                )
            except Exception:
                clients = []

        # Count leads per partner for enrichment
        leads_per_partner = {}
        revenue_per_partner = {}
        for l in user_leads:
            pid = l["partner_id"][0] if isinstance(l.get("partner_id"), (list, tuple)) else l.get("partner_id")
            if pid:
                leads_per_partner[pid] = leads_per_partner.get(pid, 0) + 1
                revenue_per_partner[pid] = revenue_per_partner.get(pid, 0) + (l.get("expected_revenue") or 0)

        for c in clients:
            terr = c.get("x_territoire")
            terr_name = terr[1] if isinstance(terr, (list, tuple)) else str(terr or "")
            tags = c.get("category_id", [])
            result["clients"].append({
                "id": c["id"],
                "name": c.get("name", ""),
                "territoire": terr_name,
                "score": c.get("x_score_client", "") or "",
                "city": c.get("city", "") or "",
                "phone": c.get("phone", "") or "",
                "email": c.get("email", "") or "",
                "website": c.get("website", "") or "",
                "street": c.get("street", "") or "",
                "zip": c.get("zip", "") or "",
                "description": c.get("x_description", "") or "",
                "facebook": c.get("x_facebook", "") or "",
                "instagram": c.get("x_instagram", "") or "",
                "linkedin": c.get("x_linkedin", "") or "",
                "google_maps": c.get("x_google_maps", "") or "",
                "type_client": c.get("x_type_client", "") or "",
                "notes_terrain": c.get("x_notes_terrain", "") or "",
                "lead_count": leads_per_partner.get(c["id"], 0),
                "pipeline_revenue": revenue_per_partner.get(c["id"], 0),
                "tag_ids": tags if isinstance(tags, list) else [],
            })

        # ── 2. Transform pipeline leads ──
        for lead in user_leads:
            partner = lead.get("partner_id")
            partner_name = partner[1] if isinstance(partner, (list, tuple)) else ""
            stage = lead.get("stage_id")
            stage_name = stage[1] if isinstance(stage, (list, tuple)) else ""
            user = lead.get("user_id")
            user_name = user[1] if isinstance(user, (list, tuple)) else ""

            # Map Odoo stage to frontend stage
            mapped_stage = STAGE_MAP.get(stage_name, stage_name or "Soumission")

            result["pipeline"].append({
                "id": lead["id"],
                "name": lead.get("name", ""),
                "stage_name": mapped_stage,
                "partner_name": partner_name,
                "expected_revenue": lead.get("expected_revenue", 0) or 0,
                "probability": lead.get("probability", 0) or 0,
                "date_deadline": lead.get("date_deadline"),
                "create_date": lead.get("create_date"),
                "user_name": user_name,
            })

        # ── 3. Compute stats ──
        total_revenue = sum(l.get("expected_revenue", 0) or 0 for l in user_leads)
        active_leads = [l for l in user_leads if l.get("probability", 0) > 0]
        avg_prob = round(sum(l.get("probability", 0) for l in active_leads) / max(len(active_leads), 1))

        # Count by stage
        stage_counts = {}
        for l in user_leads:
            stage = l.get("stage_id")
            sname = stage[1] if isinstance(stage, (list, tuple)) else str(stage or "")
            mapped = STAGE_MAP.get(sname, sname or "Soumission")
            stage_counts[mapped] = stage_counts.get(mapped, 0) + 1

        result["stats"] = {
            "client_count": len(result["clients"]),
            "lead_count": len(user_leads),
            "pipeline_revenue": total_revenue,
            "avg_probability": avg_prob,
            "stage_counts": stage_counts,
            "score_counts": {
                "A": sum(1 for c in result["clients"] if "A" in (c.get("score") or "")),
                "B": sum(1 for c in result["clients"] if "B" in (c.get("score") or "")),
                "C": sum(1 for c in result["clients"] if "C" in (c.get("score") or "")),
            },
        }

    except Exception as e:
        result["mode"] = "error"
        result["error"] = str(e)

    # ── 4. Get recent activities/messages (timeline) ──
    try:
        # Try user-filtered, then fallback to all
        activity_domain = [["res_model", "in", ["res.partner", "crm.lead"]]]
        if user_id:
            user_activity_domain = activity_domain + [["user_id", "=", user_id]]
            activities = await odoo.search_read(
                "mail.activity", user_activity_domain,
                ["res_id", "summary", "activity_type_id", "date_deadline", "state", "note"],
                order="date_deadline desc", limit=20,
            )
            if not activities:
                activities = await odoo.search_read(
                    "mail.activity", activity_domain,
                    ["res_id", "summary", "activity_type_id", "date_deadline", "state", "note"],
                    order="date_deadline desc", limit=20,
                )
        else:
            activities = await odoo.search_read(
                "mail.activity", activity_domain,
                ["res_id", "summary", "activity_type_id", "date_deadline", "state", "note"],
                order="date_deadline desc", limit=20,
            )

        for act in activities:
            act_type = act.get("activity_type_id")
            act_type_name = act_type[1] if isinstance(act_type, (list, tuple)) else str(act_type or "")
            result["activities"].append({
                "id": act.get("id"),
                "type": act_type_name,
                "summary": _s(act.get("summary")),
                "date": _s(act.get("date_deadline")),
                "state": _s(act.get("state")),
                "note": _s(act.get("note")),
                "partner_id": act.get("res_id"),
            })
    except Exception:
        pass  # Activities may not be available

    # ── 5. Build timeline from recent lead messages ──
    try:
        base_msg_domain = [["model", "=", "crm.lead"], ["message_type", "in", ["comment", "email"]]]
        msg_fields = ["date", "subject", "body", "subtype_id", "res_id"]

        messages = []
        if user_id:
            messages = await odoo.search_read(
                "mail.message",
                base_msg_domain + [["author_id.user_ids", "in", [user_id]]],
                msg_fields, order="date desc", limit=10,
            )
        if not messages:
            messages = await odoo.search_read(
                "mail.message",
                base_msg_domain,
                msg_fields, order="date desc", limit=10,
            )

        for msg in messages:
            subtype = msg.get("subtype_id")
            subtype_name = subtype[1] if isinstance(subtype, (list, tuple)) else ""
            # Clean HTML from body
            body = _s(msg.get("body", ""))
            if "<" in body:
                import re
                body = re.sub(r"<[^>]+>", "", body).strip()
            if len(body) > 100:
                body = body[:97] + "..."

            result["timeline"].append({
                "date": _s(msg.get("date", "")),
                "subject": _s(msg.get("subject", "")),
                "body": body,
                "type": subtype_name,
            })
    except Exception:
        pass  # Messages may not be accessible

    return result


@router.get("/activities", response_model=dict)
async def get_activities(
    user_id: Optional[int] = Query(None, description="Filter by user/rep ID"),
    limit: int = Query(50, ge=1, le=200),
):
    """
    Retourne les activités récentes (mail.activity) pour un représentant.
    """
    odoo = get_odoo_client()

    domain = [["res_model", "=", "res.partner"]]
    if user_id:
        domain.append(["user_id", "=", user_id])

    try:
        activities = await odoo.search_read(
            "mail.activity",
            domain,
            ["res_id", "summary", "activity_type_id", "date_deadline", "state", "note", "user_id"],
            order="date_deadline desc",
            limit=limit,
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Erreur Odoo: {str(e)}")

    formatted = []
    for act in activities:
        act_type = act.get("activity_type_id")
        act_type_name = act_type[1] if isinstance(act_type, (list, tuple)) else str(act_type or "")
        user = act.get("user_id")
        user_name = user[1] if isinstance(user, (list, tuple)) else ""

        formatted.append({
            "id": act.get("id"),
            "type": act_type_name,
            "summary": _s(act.get("summary")),
            "date": _s(act.get("date_deadline")),
            "state": _s(act.get("state")),
            "note": _s(act.get("note")),
            "partner_id": act.get("res_id"),
            "user_name": user_name,
        })

    return {
        "count": len(formatted),
        "activities": formatted,
    }
