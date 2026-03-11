"""Router Coach de Vente IA — Briefings pré-visite."""

from fastapi import APIRouter, HTTPException
from app.models.schemas import BriefingRequest, BriefingResponse
from app.services.odoo import get_odoo_client
from app.services.claude_ai import generate_briefing

router = APIRouter(prefix="/api/coach", tags=["Coach de Vente"])


@router.post("/briefing", response_model=BriefingResponse)
async def create_briefing(req: BriefingRequest):
    """Génère un briefing pré-visite IA pour un client.

    Récupère les données du client depuis Odoo, enrichit avec les leads
    et activités, puis génère un briefing stratégique avec Claude.
    """
    odoo = get_odoo_client()

    try:
        partner = await odoo.get_partner(req.partner_id)
    except ValueError:
        raise HTTPException(status_code=404, detail=f"Contact {req.partner_id} non trouvé dans Odoo")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Erreur Odoo: {str(e)}")

    # Enrichir avec leads et activités
    leads = await odoo.get_partner_leads(req.partner_id)
    activities = await odoo.get_partner_activities(req.partner_id)

    # Ajouter contexte leads/activités au prompt
    extra_context = req.context
    if leads:
        leads_text = "\n".join(
            f"- {l['name']} (étape: {l['stage_id'][1] if l.get('stage_id') else 'N/A'}, "
            f"revenu: {l.get('expected_revenue', 0)}$)"
            for l in leads[:5]
        )
        extra_context += f"\n\nOPPORTUNITÉS CRM EN COURS :\n{leads_text}"

    if activities:
        act_text = "\n".join(
            f"- {a.get('summary', 'Sans titre')} (échéance: {a.get('date_deadline', 'N/A')})"
            for a in activities[:5]
        )
        extra_context += f"\n\nACTIVITÉS PLANIFIÉES :\n{act_text}"

    try:
        briefing_text = await generate_briefing(partner, extra_context)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Erreur Claude API: {str(e)}")

    territoire = partner.get("x_territoire")
    terr_name = territoire[1] if isinstance(territoire, (list, tuple)) else str(territoire or "Non assigné")

    return BriefingResponse(
        partner_id=req.partner_id,
        partner_name=partner.get("name", "Inconnu"),
        territoire=terr_name,
        score=partner.get("x_score_client") or "N/A",
        briefing=briefing_text,
        leads_count=len(leads),
        activities_count=len(activities),
    )


@router.get("/partners", summary="Liste les clients pour sélection")
async def list_partners(
    territoire_id: int = 0,
    score: str = "",
    search: str = "",
    limit: int = 50,
):
    """Liste les clients filtrés pour le sélecteur du coach."""
    odoo = get_odoo_client()

    domain = [["is_company", "=", True]]
    if territoire_id:
        domain.append(["x_territoire", "=", territoire_id])
    if score:
        domain.append(["x_score_client", "=", score])
    if search:
        domain.append(["name", "ilike", search])

    partners = await odoo.search_read(
        "res.partner",
        domain,
        ["name", "x_territoire", "x_score_client", "city", "x_date_derniere_visite"],
        limit=limit,
        order="name asc",
    )

    return {
        "count": len(partners),
        "partners": [
            {
                "id": p["id"],
                "name": p["name"],
                "territoire": p["x_territoire"][1] if isinstance(p.get("x_territoire"), (list, tuple)) else None,
                "score": p.get("x_score_client"),
                "city": p.get("city"),
                "derniere_visite": p.get("x_date_derniere_visite"),
            }
            for p in partners
        ],
    }


@router.get("/territories", summary="Liste les territoires")
async def list_territories():
    """Liste les équipes de vente (territoires) disponibles."""
    odoo = get_odoo_client()
    teams = await odoo.search_read("crm.team", [], ["name"])
    return {"territories": [{"id": t["id"], "name": t["name"]} for t in teams]}
