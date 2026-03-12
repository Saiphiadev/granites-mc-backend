"""Pydantic schemas pour l'API Granites MC."""

from pydantic import BaseModel, Field
from typing import Optional


# ─── Coach de vente ───

class BriefingRequest(BaseModel):
    partner_id: int = Field(..., description="ID du contact Odoo")
    context: str = Field("", description="Contexte additionnel pour le briefing")


class BriefingResponse(BaseModel):
    partner_id: int
    partner_name: str
    territoire: str
    score: str
    briefing: str
    leads_count: int = 0
    activities_count: int = 0


# ─── Voix du Terrain ───

class TranscriptionResponse(BaseModel):
    text: str
    segments: list = []
    is_simulated: bool = False


class VoixSummaryRequest(BaseModel):
    transcription: str = Field(..., description="Texte de la transcription")
    partner_name: str = Field("", description="Nom du client (optionnel)")
    partner_id: Optional[int] = Field(None, description="ID du contact Odoo pour enrichir le contexte")
    context: str = Field("", description="Contexte additionnel")


class VoixSummaryResponse(BaseModel):
    summary: str
    transcription: str
    partner_name: str
    logged_to_odoo: bool = False
    note_id: Optional[int] = None


class VoixFullResponse(BaseModel):
    transcription: TranscriptionResponse
    summary: VoixSummaryResponse


# ─── CRM ───

class ClientBase(BaseModel):
    id: int
    name: str
    territoire: str
    x_score_client: Optional[str] = None
    city: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    street: Optional[str] = None
    zip: Optional[str] = None
    x_notes_terrain: Optional[str] = None
    x_competiteurs: Optional[str] = None
    x_marques_interet: Optional[str] = None
    x_date_derniere_visite: Optional[str] = None
    x_nb_visites: Optional[int] = None
    lead_count: int = 0
    # Enriched fields
    x_type_client: Optional[str] = None
    x_facebook: Optional[str] = None
    x_instagram: Optional[str] = None
    x_linkedin: Optional[str] = None
    x_google_maps: Optional[str] = None
    x_description: Optional[str] = None
    x_year_founded: Optional[str] = None
    x_employees_estimate: Optional[str] = None
    x_revenue_estimate: Optional[str] = None
    x_req_number: Optional[str] = None
    x_brands: Optional[str] = None
    x_specialties: Optional[str] = None
    x_hours: Optional[str] = None


class ClientListItem(ClientBase):
    nom_legal: Optional[str] = None
    x_territoire: Optional[list | tuple] = None


class ClientListResponse(BaseModel):
    count: int
    clients: list[ClientListItem]


class ClientDetailResponse(BaseModel):
    id: int
    name: str
    is_company: bool
    territoire: str
    x_score_client: Optional[str] = None
    city: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    street: Optional[str] = None
    zip: Optional[str] = None
    state_id: Optional[list | tuple] = None
    x_notes_terrain: Optional[str] = None
    x_competiteurs: Optional[str] = None
    x_marques_interet: Optional[str] = None
    x_date_derniere_visite: Optional[str] = None
    x_nb_visites: Optional[int] = None
    x_type_client: Optional[str] = None
    x_echantillons_notes: Optional[str] = None
    # Enriched fields
    x_facebook: Optional[str] = None
    x_instagram: Optional[str] = None
    x_linkedin: Optional[str] = None
    x_google_maps: Optional[str] = None
    x_description: Optional[str] = None
    x_year_founded: Optional[str] = None
    x_employees_estimate: Optional[str] = None
    x_revenue_estimate: Optional[str] = None
    x_req_number: Optional[str] = None
    x_brands: Optional[str] = None
    x_specialties: Optional[str] = None
    x_hours: Optional[str] = None
    child_contacts: list = []
    leads: list = []
    activities: list = []


class PipelineResponse(BaseModel):
    count: int
    leads: list


class StatsResponse(BaseModel):
    total_clients: int
    clients_by_score: dict
    total_leads: int
    pipeline_revenue: float
    pipeline_by_stage: dict
    recent_activities_count: int


class TerritoryResponse(BaseModel):
    id: int
    name: str
    client_count: int


class RepresentativeResponse(BaseModel):
    id: int
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    teams: list = []
    lead_count: int = 0
    pipeline_revenue: float = 0


# ─── Health ───

class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = "0.1.0"
    odoo_connected: bool = False
    anthropic_configured: bool = False
    deepgram_configured: bool = False
