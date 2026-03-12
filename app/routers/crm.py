"""Router CRM — Endpoints pour les données clients, pipeline, et statistiques."""

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
    limit: int = Query(500, ge=1, le=5000, description="Max results"),
):
    """
    Retourne la liste de tous les clients (contacts de type entreprise).

    Supporte les filtres par territoire, score client, et recherche textuelle.
    Format flat array compatible AG Grid.
    """
    odoo = get_odoo_client()

    domain = [["is_company", "=", True]]

    if territoire_id:
        domain.append(["x_territoire", "=", territoire_id])
    if score:
        domain.append(["x_score_client", "=", score])
    if search:
        domain = [
            "&",
            ["is_company", "=", True],
            "|", "|", "|",
            ["name", "ilike", search],
            ["city", "ilike", search],
            ["phone", "ilike", search],
            ["email", "ilike", search],
        ]

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
        terr_name = terr[1] if isinstance(terr, (list, tuple)) else str(terr or "")

        response_clients.append({
            "id": c["id"],
            "name": c.get("name", ""),
            "nom_legal": c.get("name", ""),
            "territoire": terr_name,
            "x_territoire": c.get("x_territoire"),
            "x_score_client": c.get("x_score_client", ""),
            "city": c.get("city", "") or "",
            "phone": c.get("phone", "") or "",
            "email": c.get("email", "") or "",
            "website": c.get("website", "") or "",
            "street": c.get("street", "") or "",
            "zip": c.get("zip", "") or "",
            "x_notes_terrain": c.get("x_notes_terrain", "") or "",
            "x_competiteurs": c.get("x_competiteurs", "") or "",
            "x_marques_interet": c.get("x_marques_interet", "") or "",
            "x_date_derniere_visite": None,
            "x_nb_visites": 0,
            "lead_count": 0,
            "x_type_client": c.get("x_type_client", "") or "",
            "x_facebook": c.get("x_facebook", "") or "",
            "x_instagram": c.get("x_instagram", "") or "",
            "x_linkedin": c.get("x_linkedin", "") or "",
            "x_google_maps": c.get("x_google_maps", "") or "",
            "x_description": c.get("x_description", "") or "",
            "x_year_founded": c.get("x_year_founded", "") or "",
            "x_employees_estimate": c.get("x_employees_estimate", "") or "",
            "x_revenue_estimate": c.get("x_revenue_estimate", "") or "",
            "x_req_number": c.get("x_req_number", "") or "",
            "x_brands": c.get("x_brands", "") or "",
            "x_specialties": c.get("x_specialties", "") or "",
            "x_hours": c.get("x_hours", "") or "",
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
async def get_stats():
    """
    Retourne les statistiques du CRM pour le dashboard.

    Total clients, répartition par score, par territoire,
    statistiques du pipeline, et dernière activité.
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
        total_leads = await odoo.search_count("crm.lead", [])

        # Get leads grouped by stage with total revenue
        all_leads = await odoo.search_read(
            "crm.lead",
            [],
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

    return {
        "count": len(users),
        "users": [
            {
                "id": u["id"],
                "name": u.get("name", ""),
                "email": _s(u.get("email")),
            }
            for u in users
        ],
    }
