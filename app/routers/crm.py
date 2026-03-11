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
        # Search in name, city, phone, email
        domain.append(
            [
                "|", "|", "|",
                ["name", "ilike", search],
                ["city", "ilike", search],
                ["phone", "ilike", search],
                ["email", "ilike", search],
            ]
        )

    fields = [
        "id",
        "name",
        "x_territoire",
        "x_score_client",
        "city",
        "phone",
        "email",
        "website",
        "street",
        "zip",
        "x_notes_terrain",
        "x_competiteurs",
        "x_marques_interet",
        "x_date_derniere_visite",
        "x_nb_visites",
    ]

    try:
        clients = await odoo.search_read(
            "res.partner",
            domain,
            fields,
            limit=limit,
            order="name asc",
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Erreur Odoo: {str(e)}")

    # Get lead counts per partner
    lead_counts = {}
    for client in clients:
        try:
            count = await odoo.search_count(
                "crm.lead",
                [["partner_id", "=", client["id"]]],
            )
            lead_counts[client["id"]] = count
        except Exception:
            lead_counts[client["id"]] = 0

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
            "x_score_client": c.get("x_score_client"),
            "city": c.get("city", ""),
            "phone": c.get("phone", ""),
            "email": c.get("email", ""),
            "website": c.get("website", ""),
            "street": c.get("street", ""),
            "zip": c.get("zip", ""),
            "x_notes_terrain": c.get("x_notes_terrain", ""),
            "x_competiteurs": c.get("x_competiteurs", ""),
            "x_marques_interet": c.get("x_marques_interet", ""),
            "x_date_derniere_visite": c.get("x_date_derniere_visite"),
            "x_nb_visites": c.get("x_nb_visites", 0),
            "lead_count": lead_counts.get(c["id"], 0),
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
        raise HTTPException(status_code=502, detail=f"Erreur Odoo: {str(e)}")

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
    leads = await odoo.get_partner_leads(partner_id)

    # Get recent activities
    activities = await odoo.get_partner_activities(partner_id)

    # Format territory
    terr = partner.get("x_territoire")
    terr_name = terr[1] if isinstance(terr, (list, tuple)) else str(terr or "")

    return ClientDetailResponse(
        id=partner["id"],
        name=partner.get("name", ""),
        is_company=partner.get("is_company", True),
        territoire=terr_name,
        x_score_client=partner.get("x_score_client", ""),
        city=partner.get("city", ""),
        phone=partner.get("phone", ""),
        email=partner.get("email", ""),
        website=partner.get("website", ""),
        street=partner.get("street", ""),
        zip=partner.get("zip", ""),
        state_id=partner.get("state_id"),
        x_notes_terrain=partner.get("x_notes_terrain", ""),
        x_competiteurs=partner.get("x_competiteurs", ""),
        x_marques_interet=partner.get("x_marques_interet", ""),
        x_date_derniere_visite=partner.get("x_date_derniere_visite"),
        x_nb_visites=partner.get("x_nb_visites", 0),
        x_type_client=partner.get("x_type_client", ""),
        x_echantillons_notes=partner.get("x_echantillons_notes", ""),
        child_contacts=child_contacts,
        leads=leads,
        activities=activities,
    )


@router.get("/pipeline", response_model=dict)
async def get_pipeline(limit: int = Query(500, ge=1, le=5000)):
    """
    Retourne tous les crm.lead (opportunités) du pipeline.

    Inclut le nom du partenaire associé et les informations de stage.
    """
    odoo = get_odoo_client()

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
            [],
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

        # Clients by score
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

        # Recent activities
        recent_activities = await odoo.search_read(
            "mail.activity",
            [["res_model", "=", "res.partner"]],
            ["res_id", "summary", "date_deadline", "state"],
            order="create_date desc",
            limit=10,
        )

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

    # Get client count per territory
    territories = []
    for team in teams:
        try:
            count = await odoo.search_count(
                "res.partner",
                [["is_company", "=", True], ["x_territoire", "=", team["id"]]],
            )
            territories.append({
                "id": team["id"],
                "name": team.get("name", ""),
                "client_count": count,
            })
        except Exception:
            territories.append({
                "id": team["id"],
                "name": team.get("name", ""),
                "client_count": 0,
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
            teams = await odoo.search_read(
                "crm.team",
                [["member_ids", "=", user["id"]]],
                ["id", "name"],
            )
        except Exception:
            teams = []

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
            leads = await odoo.search_read(
                "crm.lead",
                [["user_id", "=", user["id"]]],
                ["expected_revenue"],
            )
            pipeline_revenue = sum(l.get("expected_revenue", 0) for l in leads)
        except Exception:
            pipeline_revenue = 0

        team_names = [t["name"] for t in teams] if teams else []

        representatives.append({
            "id": user["id"],
            "name": user.get("name", ""),
            "email": user.get("email", ""),
            "phone": user.get("phone", ""),
            "teams": team_names,
            "lead_count": lead_count,
            "pipeline_revenue": pipeline_revenue,
        })

    return {
        "count": len(representatives),
        "reps": representatives,
    }
