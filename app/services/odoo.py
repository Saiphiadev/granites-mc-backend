"""Connecteur Odoo JSON-RPC pour Granites MC."""

import httpx
from typing import Any
from app.config import get_settings


class OdooClient:
    """Client Odoo via JSON-RPC (session-based auth)."""

    def __init__(self):
        self.settings = get_settings()
        self.base_url = self.settings.odoo_url
        self.db = self.settings.odoo_db
        self.uid: int | None = None
        self._session_cookies: dict = {}
        self._client = httpx.AsyncClient(timeout=30.0)

    async def authenticate(self) -> int:
        """Authenticate and return user ID."""
        resp = await self._client.post(
            f"{self.base_url}/web/session/authenticate",
            json={
                "jsonrpc": "2.0",
                "method": "call",
                "id": 1,
                "params": {
                    "db": self.db,
                    "login": self.settings.odoo_user,
                    "password": self.settings.odoo_password,
                },
            },
        )
        data = resp.json()
        if data.get("error"):
            raise ConnectionError(f"Odoo auth failed: {data['error']}")
        self.uid = data["result"]["uid"]
        self._session_cookies = dict(resp.cookies)
        return self.uid

    async def _call_kw(
        self, model: str, method: str, args: list, kwargs: dict | None = None
    ) -> Any:
        """Generic JSON-RPC call to Odoo."""
        if not self.uid:
            await self.authenticate()

        resp = await self._client.post(
            f"{self.base_url}/web/dataset/call_kw",
            json={
                "jsonrpc": "2.0",
                "method": "call",
                "id": 2,
                "params": {
                    "model": model,
                    "method": method,
                    "args": args,
                    "kwargs": kwargs or {},
                },
            },
            cookies=self._session_cookies,
        )
        data = resp.json()
        if data.get("error"):
            raise Exception(f"Odoo error: {data['error']['data']['message']}")
        return data["result"]

    async def search_read(
        self,
        model: str,
        domain: list,
        fields: list[str],
        limit: int = 0,
        order: str = "",
    ) -> list[dict]:
        """Search and read records."""
        kwargs = {"fields": fields}
        if limit:
            kwargs["limit"] = limit
        if order:
            kwargs["order"] = order
        return await self._call_kw(model, "search_read", [domain], kwargs)

    async def read(self, model: str, ids: list[int], fields: list[str]) -> list[dict]:
        """Read records by IDs."""
        return await self._call_kw(model, "read", [ids], {"fields": fields})

    async def search_count(self, model: str, domain: list) -> int:
        """Count matching records."""
        return await self._call_kw(model, "search_count", [domain])

    async def create(self, model: str, values: dict) -> int:
        """Create a record and return its ID."""
        return await self._call_kw(model, "create", [values])

    async def write(self, model: str, ids: list[int], values: dict) -> bool:
        """Update records by IDs."""
        return await self._call_kw(model, "write", [ids, values])

    async def fields_get(
        self, model: str, attributes: list[str] | None = None
    ) -> dict:
        """Get field definitions for a model."""
        kwargs = {}
        if attributes:
            kwargs["attributes"] = attributes
        return await self._call_kw(model, "fields_get", [], kwargs)

    # ─── Méthodes métier spécifiques Granites MC ───

    async def get_partner(self, partner_id: int) -> dict:
        """Get full partner details for coach briefing."""
        fields = [
            "name",
            "is_company",
            "phone",
            "email",
            "website",
            "street",
            "city",
            "state_id",
            "zip",
            "x_territoire",
            "x_score_client",
            "x_notes_terrain",
            "x_type_client",
            "x_competiteurs",
            "x_marques_interet",
            "x_date_derniere_visite",
            "x_nb_visites",
            "x_echantillons_notes",
            "x_facebook",
            "x_instagram",
            "x_linkedin",
            "x_google_maps",
            "x_description",
            "x_year_founded",
            "x_employees_estimate",
            "x_revenue_estimate",
            "x_req_number",
            "x_brands",
            "x_specialties",
            "x_hours",
            # Isabelle fields
            "x_freq_visite",
            "x_date_premiere_visite",
            "x_meilleure_annee",
            "x_ventes_2019",
            "x_ventes_2020",
            "x_ventes_2021",
            "x_ventes_2022",
            "x_ventes_2023",
            "x_ventes_total",
            "x_contact_principal",
            "x_contact_secondaire",
            "x_echantillons_livres",
            "x_historique_visites",
            "x_bon_soumission",
            "x_provenance",
            "x_salle_montre",
            "x_notes_isabelle",
            "category_id",
            "activity_ids",
            "message_ids",
        ]
        records = await self.read("res.partner", [partner_id], fields)
        if not records:
            raise ValueError(f"Partner {partner_id} not found")
        return records[0]

    async def get_partner_activities(self, partner_id: int) -> list[dict]:
        """Get scheduled activities for a partner."""
        return await self.search_read(
            "mail.activity",
            [["res_model", "=", "res.partner"], ["res_id", "=", partner_id]],
            [
                "activity_type_id",
                "summary",
                "note",
                "date_deadline",
                "state",
                "user_id",
            ],
            order="date_deadline asc",
        )

    async def get_partner_leads(self, partner_id: int) -> list[dict]:
        """Get CRM leads/opportunities for a partner."""
        return await self.search_read(
            "crm.lead",
            [["partner_id", "=", partner_id]],
            [
                "name",
                "stage_id",
                "expected_revenue",
                "probability",
                "date_deadline",
                "description",
                "tag_ids",
                "create_date",
            ],
            order="create_date desc",
            limit=10,
        )

    async def get_territory_stats(self, team_id: int) -> dict:
        """Get territory statistics."""
        total = await self.search_count(
            "res.partner",
            [["is_company", "=", True], ["x_territoire", "=", team_id]],
        )
        score_a = await self.search_count(
            "res.partner",
            [
                ["is_company", "=", True],
                ["x_territoire", "=", team_id],
                ["x_score_client", "=", "A"],
            ],
        )
        score_b = await self.search_count(
            "res.partner",
            [
                ["is_company", "=", True],
                ["x_territoire", "=", team_id],
                ["x_score_client", "=", "B"],
            ],
        )
        return {"total": total, "score_a": score_a, "score_b": score_b}

    async def create_activity(
        self,
        partner_id: int,
        activity_type_id: int,
        summary: str,
        note: str,
        date_deadline: str,
        user_id: int,
    ) -> int:
        """Create a scheduled activity on a partner."""
        return await self._call_kw(
            "mail.activity",
            "create",
            [
                {
                    "res_model_id": (
                        await self._call_kw(
                            "ir.model",
                            "search",
                            [[["model", "=", "res.partner"]]],
                        )
                    )[0],
                    "res_id": partner_id,
                    "activity_type_id": activity_type_id,
                    "summary": summary,
                    "note": note,
                    "date_deadline": date_deadline,
                    "user_id": user_id,
                }
            ],
        )

    async def log_note(self, partner_id: int, body: str) -> int:
        """Post an internal note on a partner."""
        return await self._call_kw(
            "res.partner",
            "message_post",
            [partner_id],
            {
                "body": body,
                "message_type": "comment",
                "subtype_xmlid": "mail.mt_note",
            },
        )

    async def get_child_contacts(self, partner_id: int, limit: int = 50) -> list[dict]:
        """Get child contacts (people) for a company partner."""
        return await self.search_read(
            "res.partner",
            [["parent_id", "=", partner_id], ["is_company", "=", False]],
            ["id", "name", "email", "phone", "function"],
            limit=limit,
            order="name asc",
        )

    async def get_pipeline_stats(self) -> dict:
        """Get CRM pipeline statistics."""
        leads = await self.search_read(
            "crm.lead",
            [],
            ["stage_id", "expected_revenue"],
            limit=1000,
        )

        pipeline_revenue = 0
        stage_stats = {}
        for lead in leads:
            stage = lead.get("stage_id")
            stage_name = stage[1] if isinstance(stage, (list, tuple)) else str(stage)

            if stage_name not in stage_stats:
                stage_stats[stage_name] = {"count": 0, "revenue": 0}

            stage_stats[stage_name]["count"] += 1
            revenue = lead.get("expected_revenue", 0)
            stage_stats[stage_name]["revenue"] += revenue
            pipeline_revenue += revenue

        return {
            "total_revenue": pipeline_revenue,
            "by_stage": stage_stats,
        }

    async def get_user_stats(self, user_id: int) -> dict:
        """Get statistics for a specific user/representative."""
        leads = await self.search_read(
            "crm.lead",
            [["user_id", "=", user_id]],
            ["expected_revenue"],
        )

        pipeline_revenue = sum(l.get("expected_revenue", 0) for l in leads)
        lead_count = len(leads)

        return {
            "lead_count": lead_count,
            "pipeline_revenue": pipeline_revenue,
        }

    async def close(self):
        """Close the HTTP client."""
        await self._client.aclose()


# Singleton
_client: OdooClient | None = None


def get_odoo_client() -> OdooClient:
    global _client
    if _client is None:
        _client = OdooClient()
    return _client
