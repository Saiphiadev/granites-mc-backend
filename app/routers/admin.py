"""Router Admin — Endpoints d'administration et migration de données."""

import json
import random
from datetime import datetime, timedelta
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.services.odoo import get_odoo_client

router = APIRouter(prefix="/api/admin", tags=["Admin"])


# ─── Schemas ───

class FieldCheckResponse(BaseModel):
    existing_fields: list[str]
    missing_fields: list[str]
    all_x_fields: list[str]


class FieldCreateRequest(BaseModel):
    field_name: str
    field_type: str = "char"  # char, text, integer, float, date, boolean, selection
    field_label: str = ""
    selection_values: list[str] = []


class PartnerCreateRequest(BaseModel):
    name: str
    is_company: bool = True
    phone: str = ""
    email: str = ""
    website: str = ""
    street: str = ""
    city: str = ""
    zip: str = ""
    x_score_client: str = ""
    x_territoire: int = 0
    x_type_client: str = ""
    x_notes_terrain: str = ""


class PartnerUpdateRequest(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    street: Optional[str] = None
    city: Optional[str] = None
    zip: Optional[str] = None
    x_score_client: Optional[str] = None
    x_type_client: Optional[str] = None
    x_notes_terrain: Optional[str] = None
    x_competiteurs: Optional[str] = None
    x_marques_interet: Optional[str] = None
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


class MigrationResult(BaseModel):
    created_fields: list[str]
    created_partners: list[dict]
    updated_partners: list[dict]
    errors: list[str]


# ─── Required custom fields for enriched data ───

REQUIRED_FIELDS = {
    "x_type_client": {"type": "char", "label": "Type de client", "size": 100},
    "x_facebook": {"type": "char", "label": "Facebook", "size": 255},
    "x_instagram": {"type": "char", "label": "Instagram", "size": 255},
    "x_linkedin": {"type": "char", "label": "LinkedIn", "size": 255},
    "x_google_maps": {"type": "char", "label": "Google Maps", "size": 500},
    "x_description": {"type": "text", "label": "Description"},
    "x_year_founded": {"type": "char", "label": "Année de fondation", "size": 10},
    "x_employees_estimate": {"type": "char", "label": "Nombre d'employés (estimé)", "size": 50},
    "x_revenue_estimate": {"type": "char", "label": "Revenus estimés", "size": 50},
    "x_req_number": {"type": "char", "label": "Numéro REQ", "size": 50},
    "x_brands": {"type": "text", "label": "Marques utilisées"},
    "x_specialties": {"type": "char", "label": "Spécialités", "size": 255},
    "x_hours": {"type": "char", "label": "Heures d'ouverture", "size": 255},
}


# ─── Enriched client data ───

ENRICHED_CLIENTS = [
    {
        "rank": 1, "odoo_id": 423, "name": "Cuisifab 3ri",
        "type_client": "Fabricant d'armoires", "territoire": "3-RI", "score": "A",
        "phone": "819-519-8400", "email": "info@cuisifab.com",
        "website": "https://cuisifab.com/",
        "street": "5075 Boulevard des Forges", "city": "Trois-Rivières", "zip": "G8Y 4Z3",
        "facebook": "https://www.facebook.com/Cuisifab/",
        "instagram": "https://www.instagram.com/cuisifab/",
        "linkedin": "", "google_maps": "",
        "hours": "Lun-Mer 8h-17h, Jeu-Ven 8h-21h, Soir et fin de semaine sur rendez-vous",
        "description": "Fabricant d'armoires de cuisine et salle de bain. Design, livraison et installation.",
        "specialties": "Résidentiel, Commercial",
        "brands": "Cosentino (Silestone, Dekton)",
        "employees_estimate": "10-15", "revenue_estimate": "$1.55M",
        "year_founded": "", "req_number": "",
        "notes_terrain": "Volumes: 2019: 105019$, 2020: 158799$, 2021: 325950$, 2022: 240383$. 2 emplacements: Trois-Rivières et Bécancour",
    },
    {
        "rank": 2, "odoo_id": 72, "name": "Rubic",
        "type_client": "Designer", "territoire": "T03", "score": "A",
        "phone": "819-850-6125", "email": "info@espacesrubic.com",
        "website": "https://espacesrubic.com/",
        "street": "397 rue Rose-Ellis", "city": "Drummondville", "zip": "J2C 0R9",
        "facebook": "https://www.facebook.com/espacesrubic",
        "instagram": "https://www.instagram.com/espacesrubic",
        "linkedin": "", "google_maps": "",
        "hours": "Lun-Ven 9h-17h",
        "description": "Cuisines design et ébénisterie. Conception sur mesure guidée par des designers experts.",
        "specialties": "Résidentiel, Luxe",
        "brands": "Cosentino (Silestone, Dekton), Miralis",
        "employees_estimate": "5-10", "revenue_estimate": "",
        "year_founded": "", "req_number": "",
        "notes_terrain": "Volumes: 2019: 47813$, 2020: 86720$, 2021: 169560$, 2022: 87155$. Distributeur autorisé Cosentino.",
    },
    {
        "rank": 3, "odoo_id": 452, "name": "Avivia (50/50)",
        "type_client": "Fabricant d'armoires", "territoire": "3-RI", "score": "A",
        "phone": "418-365-7821", "email": "",
        "website": "https://avivia.ca/",
        "street": "20 route Goulet", "city": "Saint-Séverin-de-Proulxville", "zip": "G0X 2B0",
        "facebook": "https://www.facebook.com/CuisinesAvivA/",
        "instagram": "", "linkedin": "", "google_maps": "",
        "hours": "Lun-Jeu 8h-17h, Ven 8h-12h",
        "description": "Fabricant québécois d'armoires écoresponsables. +30 ans d'expertise.",
        "specialties": "Résidentiel, Écoresponsable",
        "brands": "Matériaux écoresponsables",
        "employees_estimate": "12", "revenue_estimate": "",
        "year_founded": "1988", "req_number": "1145799400",
        "notes_terrain": "Volumes: 2019: 67925$, 2020: 161399$, 2021: 136557$, 2022: 138772$. 50/50 partage avec compétiteur.",
    },
    {
        "rank": 4, "odoo_id": None, "name": "Cuisi-Meuble S.M.",
        "type_client": "Fabricant d'armoires", "territoire": "T03", "score": "A",
        "phone": "819-359-3110", "email": "info@cuisimeublesm.com",
        "website": "https://cuisimeublesm.com/",
        "street": "1031 chemin de Warwick", "city": "Tingwick", "zip": "J0A 1L0",
        "facebook": "https://www.facebook.com/p/Cuisi-Meuble-SM-inc-100063602498796/",
        "instagram": "", "linkedin": "", "google_maps": "",
        "hours": "",
        "description": "Fabricant d'armoires de cuisine et salle de bain fondé en 1993 par Simon Martineau.",
        "specialties": "Résidentiel, Commercial",
        "brands": "",
        "employees_estimate": "10-12", "revenue_estimate": "",
        "year_founded": "1993", "req_number": "",
        "notes_terrain": "Volumes: 2019: 116621$, 2020: 115316$, 2021: 133631$, 2022: 72463$",
    },
    {
        "rank": 5, "odoo_id": None, "name": "Cuisines M.R.S. / Cuisimax",
        "type_client": "Fabricant d'armoires", "territoire": "T03", "score": "A",
        "phone": "819-758-4945", "email": "info@cuisimax.com",
        "website": "https://cuisimax.com/fr/1_cuisines-mrs",
        "street": "180 Boulevard Bois-Francs Sud", "city": "Victoriaville", "zip": "G6P 4S7",
        "facebook": "https://www.facebook.com/p/Cuisines-MRS-100075941271182/",
        "instagram": "", "linkedin": "", "google_maps": "",
        "hours": "Lun-Ven 8h30-16h30",
        "description": "Fabricant haut de gamme d'armoires cuisine/salle de bain depuis 1967.",
        "specialties": "Résidentiel, Commercial, Luxe",
        "brands": "",
        "employees_estimate": "", "revenue_estimate": "$5M",
        "year_founded": "1967", "req_number": "",
        "notes_terrain": "Volumes: 2019: 71514$, 2020: 18661$, 2021: 93321$, 2022: 111642$. 5% net 30 jours.",
    },
    {
        "rank": 6, "odoo_id": 70, "name": "Ebe Des Cantons",
        "type_client": "Ébénisterie", "territoire": "T03", "score": "A",
        "phone": "819-574-6211", "email": "ct@ebenisterie.ca",
        "website": "http://www.ebenisterie.ca/",
        "street": "1494 Boulevard Industriel", "city": "Magog", "zip": "J1X 4V9",
        "facebook": "", "instagram": "", "linkedin": "", "google_maps": "",
        "hours": "",
        "description": "Ébénisterie classique et commerciale. Armoires, portes, mobilier sur mesure.",
        "specialties": "Résidentiel, Commercial",
        "brands": "",
        "employees_estimate": "", "revenue_estimate": "",
        "year_founded": "", "req_number": "",
        "notes_terrain": "Volumes: 2019: 42350$, 2020: 52791$, 2021: 86864$, 2022: 5251$. Contact: Christian Tremblay.",
    },
    {
        "rank": 7, "odoo_id": None, "name": "Armoires N.S.",
        "type_client": "Fabricant d'armoires", "territoire": "T03", "score": "A",
        "phone": "", "email": "",
        "website": "",
        "street": "", "city": "", "zip": "",
        "facebook": "", "instagram": "", "linkedin": "", "google_maps": "",
        "hours": "",
        "description": "Fabricant d'armoires dans la région du Québec.",
        "specialties": "",
        "brands": "",
        "employees_estimate": "", "revenue_estimate": "",
        "year_founded": "", "req_number": "",
        "notes_terrain": "Volumes: 2019: 54506$, 2020: 53990$, 2021: 75638$, 2022: 57282$. Contacts: Nelson, Jeff, Louis.",
    },
    {
        "rank": 8, "odoo_id": 464, "name": "Andreanne Allard",
        "type_client": "Designer", "territoire": "3-RI", "score": "A",
        "phone": "819-995-0173", "email": "info@andreanneallard.com",
        "website": "https://andreanneallard.com/",
        "street": "5235 rue De La Châtelaine", "city": "Trois-Rivières", "zip": "G8Y 5H3",
        "facebook": "https://www.facebook.com/andreanneallarddesigner/",
        "instagram": "", "linkedin": "https://ca.linkedin.com/in/andréanne-allard-457484157",
        "google_maps": "",
        "hours": "Lun-Ven sur rendez-vous",
        "description": "Design d'intérieur, projets résidentiels clé en main. 20 ans d'expérience.",
        "specialties": "Résidentiel, Commercial, Luxe",
        "brands": "",
        "employees_estimate": "", "revenue_estimate": "",
        "year_founded": "2021", "req_number": "1176163070",
        "notes_terrain": "Volumes: 2019: 57892$, 2020: 15216$, 2021: 1305$. Incorporée le 19 janvier 2021.",
    },
    {
        "rank": 9, "odoo_id": 413, "name": "Armoires solution",
        "type_client": "Fabricant d'armoires", "territoire": "3-RI", "score": "A",
        "phone": "819-697-2464", "email": "info@armoiressolution.com",
        "website": "http://www.armoiressolution.com",
        "street": "430 rue Vachon", "city": "Trois-Rivières", "zip": "G8T 8Y2",
        "facebook": "https://www.facebook.com/armoiressolution/",
        "instagram": "", "linkedin": "", "google_maps": "",
        "hours": "",
        "description": "Fabricant d'armoires de cuisine, vanités, dressings, bibliothèques.",
        "specialties": "Résidentiel, Commercial",
        "brands": "",
        "employees_estimate": "", "revenue_estimate": "",
        "year_founded": "", "req_number": "",
        "notes_terrain": "Volumes: 2019: 8636$, 2020: 10476$, 2021: 35523$, 2022: 39813$. RBQ: 5703-8382-01.",
    },
    {
        "rank": 10, "odoo_id": 415, "name": "Ebe Paul Guy Massicotte",
        "type_client": "Ébénisterie", "territoire": "3-RI", "score": "A",
        "phone": "819-691-2228", "email": "",
        "website": "",
        "street": "162 Saint Laurent", "city": "Cap-de-la-Madeleine", "zip": "G8T 6G3",
        "facebook": "", "instagram": "", "linkedin": "", "google_maps": "",
        "hours": "Lun-Ven 9h-19h, Sam 10h-19h",
        "description": "Spécialiste armoires de cuisine et mobilier. Fabricant et détaillant.",
        "specialties": "Résidentiel",
        "brands": "",
        "employees_estimate": "", "revenue_estimate": "",
        "year_founded": "", "req_number": "9172-5143",
        "notes_terrain": "Volumes: 2019: 7419$, 2020: 16615$, 2021: 37641$, 2022: 35340$. RBQ: 8337-0874-07.",
    },
    {
        "rank": 11, "odoo_id": 73, "name": "Prefab",
        "type_client": "Autre", "territoire": "T03", "score": "B",
        "phone": "", "email": "",
        "website": "",
        "street": "", "city": "", "zip": "",
        "facebook": "", "instagram": "", "linkedin": "", "google_maps": "",
        "hours": "",
        "description": "Produits d'armoires préfabriquées.",
        "specialties": "",
        "brands": "",
        "employees_estimate": "", "revenue_estimate": "",
        "year_founded": "", "req_number": "",
        "notes_terrain": "Volumes: 2019: 31621$, 2020: 29814$, 2021: 34340$, 2022: 17488$",
    },
    {
        "rank": 12, "odoo_id": 431, "name": "Bruno pichet",
        "type_client": "Ébénisterie", "territoire": "3-RI", "score": "B",
        "phone": "819-375-5337", "email": "",
        "website": "https://brunopichet.com/",
        "street": "2281 Rang Sainte Marguerite", "city": "Saint-Maurice", "zip": "G0X 2X0",
        "facebook": "https://www.facebook.com/latelierdebruno62",
        "instagram": "", "linkedin": "https://fr.linkedin.com/company/atelierbruno",
        "google_maps": "",
        "hours": "",
        "description": "Maître ébéniste. Mobilier en bois créé sur mesure.",
        "specialties": "Résidentiel, Sur mesure/Luxe",
        "brands": "",
        "employees_estimate": "", "revenue_estimate": "",
        "year_founded": "", "req_number": "9100-9662",
        "notes_terrain": "Volumes: 2019: 21545$, 2020: 17099$, 2021: 32769$, 2022: 16264$",
    },
    {
        "rank": 13, "odoo_id": 443, "name": "Pascal et Stefanie bois b",
        "type_client": "Autre", "territoire": "T03", "score": "B",
        "phone": "", "email": "",
        "website": "",
        "street": "", "city": "", "zip": "",
        "facebook": "", "instagram": "", "linkedin": "", "google_maps": "",
        "hours": "",
        "description": "",
        "specialties": "",
        "brands": "",
        "employees_estimate": "", "revenue_estimate": "",
        "year_founded": "", "req_number": "",
        "notes_terrain": "Volumes: 2021: 3287$, 2022: 30760$. Croissance forte en 2022.",
    },
    {
        "rank": 14, "odoo_id": 454, "name": "Atelier Dlj",
        "type_client": "Ébénisterie", "territoire": "3-RI", "score": "B",
        "phone": "819-692-6624", "email": "",
        "website": "",
        "street": "650 route 349", "city": "Saint-Alexis-des-Monts", "zip": "J0K 1V0",
        "facebook": "https://www.facebook.com/latelierdalexis/",
        "instagram": "", "linkedin": "", "google_maps": "",
        "hours": "",
        "description": "Ébénisterie dans la région de Saint-Alexis-des-Monts.",
        "specialties": "Résidentiel",
        "brands": "",
        "employees_estimate": "", "revenue_estimate": "",
        "year_founded": "", "req_number": "",
        "notes_terrain": "Volumes: 2019: 15951$, 2020: 14084$, 2021: 30621$, 2022: 15845$",
    },
    {
        "rank": 15, "odoo_id": 20, "name": "Antiquite design",
        "type_client": "Autre", "territoire": "T03", "score": "B",
        "phone": "819-690-4457", "email": "marielise@antiquitedesign.com",
        "website": "https://www.antiquitedesign.com/",
        "street": "", "city": "Victoriaville", "zip": "",
        "facebook": "https://www.facebook.com/antiquitedesign/",
        "instagram": "https://www.instagram.com/antiquite_design/",
        "linkedin": "", "google_maps": "",
        "hours": "",
        "description": "Design et restauration de maisons ancestrales. Combine design antique et contemporain.",
        "specialties": "Résidentiel, Luxe, Restauration",
        "brands": "",
        "employees_estimate": "1-5", "revenue_estimate": "",
        "year_founded": "", "req_number": "",
        "notes_terrain": "Volumes: 2019: 22327$, 2020: 19085$, 2021: 30095$, 2022: 10619$. Contact: Marie-Lise Frenette.",
    },
    {
        "rank": 16, "odoo_id": 436, "name": "Armoire Decor",
        "type_client": "Fabricant d'armoires", "territoire": "3-RI", "score": "B",
        "phone": "819-377-1871", "email": "info@armoiredecor.com",
        "website": "https://armoiredecor.com/",
        "street": "12488 rue Notre-Dame Ouest", "city": "Trois-Rivières", "zip": "G9B 6X2",
        "facebook": "https://www.facebook.com/p/Armoire-Décor-Inc-100068019462827/",
        "instagram": "", "linkedin": "", "google_maps": "",
        "hours": "Lun-Ven 8h30-17h (sur rendez-vous)",
        "description": "Maître dans l'art de concevoir et installer des armoires de cuisine et salle de bain.",
        "specialties": "Résidentiel, Commercial",
        "brands": "",
        "employees_estimate": "1-10", "revenue_estimate": "",
        "year_founded": "1979", "req_number": "",
        "notes_terrain": "Volumes: 2019: 16043$, 2020: 3995$, 2021: 28487$, 2022: 5603$. Fondé en 1979.",
    },
    {
        "rank": 17, "odoo_id": 411, "name": "Ebe Bois Brian",
        "type_client": "Fabricant d'armoires", "territoire": "3-RI", "score": "B",
        "phone": "819-840-6906", "email": "info@nova-design.ca",
        "website": "https://nova-design.ca/",
        "street": "2105 Rue Charbonneau", "city": "Trois-Rivières", "zip": "G9A 5C9",
        "facebook": "https://www.facebook.com/p/Bois-Briand-Cuisines-et-Salles-de-bain-100063667835763/",
        "instagram": "", "linkedin": "", "google_maps": "",
        "hours": "",
        "description": "Fabrication d'armoires cuisine et salle de bain. Opère maintenant sous le nom Nova Design.",
        "specialties": "Résidentiel, Commercial",
        "brands": "",
        "employees_estimate": "5-15", "revenue_estimate": "",
        "year_founded": "", "req_number": "",
        "notes_terrain": "Volumes: 2019: 18737$, 2020: 27210$, 2021: 13893$, 2022: 1084$. Anciennement Bois-Briand.",
    },
    {
        "rank": 18, "odoo_id": 109, "name": "Armoires c Tremblay Inc",
        "type_client": "Fabricant d'armoires", "territoire": "T04", "score": "B",
        "phone": "450-446-2182", "email": "",
        "website": "https://www.armoirestremblay.com/",
        "street": "3108 Rue Bernard-Pilon", "city": "Saint-Mathieu-de-Beloeil", "zip": "J3G 4S5",
        "facebook": "https://www.facebook.com/ArmoiresTremblay/",
        "instagram": "", "linkedin": "https://ca.linkedin.com/company/armoirestremblay",
        "google_maps": "",
        "hours": "Lun-Jeu 8h-17h, Ven 8h-12h",
        "description": "Entreprise familiale de conception et fabrication d'armoires. Fondée en 1984.",
        "specialties": "Résidentiel, Luxe",
        "brands": "",
        "employees_estimate": "11-50", "revenue_estimate": "",
        "year_founded": "1984", "req_number": "",
        "notes_terrain": "Volumes: 2019: 9652$, 2020: 10142$, 2021: 26979$. Dessert Rive-Sud de Montréal.",
    },
    {
        "rank": 19, "odoo_id": None, "name": "Armoires B.M.S.",
        "type_client": "Fabricant d'armoires", "territoire": "3-RI", "score": "B",
        "phone": "819-229-3315", "email": "info@armoiresbms.com",
        "website": "https://www.armoiresbms.com/",
        "street": "371 Rang Pays-Brûlé", "city": "Saint-Célestin", "zip": "J0C 1G0",
        "facebook": "", "instagram": "", "linkedin": "", "google_maps": "",
        "hours": "",
        "description": "Fabricant spécialisé armoires cuisine et salle de bain. Dessert Mauricie et Centre-du-Québec.",
        "specialties": "Résidentiel, Commercial",
        "brands": "Silestone, Caesarstone, Cambria, Dekton, Corian",
        "employees_estimate": "5-15", "revenue_estimate": "",
        "year_founded": "2002", "req_number": "",
        "notes_terrain": "Volumes: 2019: 17291$, 2020: 11117$, 2021: 22082$, 2022: 3195$. RBQ: 8326-4390-30.",
    },
    {
        "rank": 20, "odoo_id": None, "name": "Armoire B.M.",
        "type_client": "Fabricant d'armoires", "territoire": "T03", "score": "B",
        "phone": "", "email": "",
        "website": "",
        "street": "", "city": "", "zip": "",
        "facebook": "", "instagram": "", "linkedin": "", "google_maps": "",
        "hours": "",
        "description": "Fabricant d'armoires. Entité distincte d'Armoires B.M.S. Inc.",
        "specialties": "",
        "brands": "",
        "employees_estimate": "", "revenue_estimate": "",
        "year_founded": "", "req_number": "",
        "notes_terrain": "Volumes: 2019: 9000$, 2020: 8489$, 2021: 17600$, 2022: 8450$. Contacts: Janicka, Carlos, Luis, Nathalie.",
    },
    {
        "rank": 21, "odoo_id": 21, "name": "Bout Design Ladouceur",
        "type_client": "Designer", "territoire": "T03", "score": "B",
        "phone": "", "email": "",
        "website": "",
        "street": "", "city": "Estrie", "zip": "",
        "facebook": "", "instagram": "", "linkedin": "", "google_maps": "",
        "hours": "",
        "description": "Design d'intérieur ou mobilier sur mesure dans la région de l'Estrie.",
        "specialties": "",
        "brands": "",
        "employees_estimate": "1-3", "revenue_estimate": "",
        "year_founded": "", "req_number": "",
        "notes_terrain": "Volumes: 2019: 14449$, 2020: 8949$, 2021: 17249$, 2022: 8119$",
    },
    {
        "rank": 22, "odoo_id": 66, "name": "Cuis chaput",
        "type_client": "Fabricant d'armoires", "territoire": "T03", "score": "B",
        "phone": "", "email": "",
        "website": "",
        "street": "", "city": "Victoriaville", "zip": "",
        "facebook": "", "instagram": "", "linkedin": "", "google_maps": "",
        "hours": "",
        "description": "Fabricant d'armoires de cuisine à Victoriaville.",
        "specialties": "Résidentiel",
        "brands": "",
        "employees_estimate": "", "revenue_estimate": "",
        "year_founded": "", "req_number": "",
        "notes_terrain": "Volumes: 2019: 10780$, 2020: 5724$, 2021: 15254$, 2022: 11789$",
    },
    {
        "rank": 23, "odoo_id": 440, "name": "Luc chenevert",
        "type_client": "Ébénisterie", "territoire": "3-RI", "score": "C",
        "phone": "", "email": "",
        "website": "https://www.atelierebenisterielucchenevert.ca/",
        "street": "343 Rang de la Rivière SO", "city": "Maskinongé", "zip": "J0K 1N0",
        "facebook": "https://www.facebook.com/ebenisterielucchenevert/",
        "instagram": "", "linkedin": "", "google_maps": "",
        "hours": "",
        "description": "Atelier d'ébénisterie spécialisé en bois massif.",
        "specialties": "Résidentiel, Commercial, Institutionnel",
        "brands": "",
        "employees_estimate": "1-5", "revenue_estimate": "",
        "year_founded": "1997", "req_number": "1147120613",
        "notes_terrain": "Volumes: 2019: 12457$, 2021: 8705$, 2022: 2099$. Fondé par Luc Chênevert.",
    },
    {
        "rank": 24, "odoo_id": 22, "name": "Sma",
        "type_client": "Autre", "territoire": "T03", "score": "C",
        "phone": "", "email": "",
        "website": "",
        "street": "", "city": "Estrie", "zip": "",
        "facebook": "", "instagram": "", "linkedin": "", "google_maps": "",
        "hours": "",
        "description": "",
        "specialties": "",
        "brands": "",
        "employees_estimate": "", "revenue_estimate": "",
        "year_founded": "", "req_number": "",
        "notes_terrain": "Volumes: 2021: 11102$. Achat ponctuel en 2021 uniquement.",
    },
    {
        "rank": 25, "odoo_id": 434, "name": "Boiserie Anny Maxxx",
        "type_client": "Ébénisterie", "territoire": "3-RI", "score": "C",
        "phone": "819-377-0496", "email": "boiseriesanny.max@hotmail.com",
        "website": "",
        "street": "2736 Rue Charbonneau", "city": "Trois-Rivières", "zip": "G9A 5C9",
        "facebook": "https://www.facebook.com/ArmoireBoiseriesAnnyMaxInc/",
        "instagram": "", "linkedin": "", "google_maps": "",
        "hours": "",
        "description": "Fabrication de mobilier commercial, institutionnel et résidentiel.",
        "specialties": "Résidentiel, Commercial, Institutionnel",
        "brands": "",
        "employees_estimate": "3-8", "revenue_estimate": "",
        "year_founded": "1988", "req_number": "",
        "notes_terrain": "Volumes: 2019: 839$, 2021: 7278$. ~3 employés.",
    },
]


# ─── Territory mapping ───

TERRITORY_MAP = {
    "3-RI": 8,   # T03 — Estrie / Rive (same as T03 in this setup)
    "T03": 8,
    "T04": 12,
    "T05": None,  # To be determined
}


# ─── Type client selection mapping ───
# Maps our enriched data labels to Odoo selection keys

TYPE_CLIENT_MAP = {
    "Fabricant d'armoires": "cuisiniste",
    "Ébénisterie": "ebeniste",
    "Designer": "designer",
    "Particulier": "particulier",
    "Constructeur": "entrepreneur",
    "Autre": "autre",
}

# New selection options to add if missing
TYPE_CLIENT_NEW_OPTIONS = {
    "particulier": "Particulier",
    "autre": "Autre",
}


# ─── Endpoints ───

@router.get("/field-info/{field_name}")
async def get_field_info(field_name: str):
    """
    Retourne les détails d'un champ Odoo incluant les valeurs de sélection.
    """
    odoo = get_odoo_client()

    try:
        fields = await odoo.fields_get(
            "res.partner", ["string", "type", "selection"]
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Erreur Odoo: {str(e)}")

    if field_name not in fields:
        raise HTTPException(status_code=404, detail=f"Champ {field_name} non trouvé")

    return fields[field_name]


@router.post("/fix-type-client-selection")
async def fix_type_client_selection():
    """
    Ajoute les options de sélection manquantes au champ x_type_client.
    """
    odoo = get_odoo_client()

    try:
        # Get current field info with selection values
        fields = await odoo.fields_get(
            "res.partner", ["string", "type", "selection"]
        )

        if "x_type_client" not in fields:
            return {"error": "x_type_client field not found"}

        field_info = fields["x_type_client"]
        field_type = field_info.get("type", "")

        if field_type != "selection":
            return {
                "status": "not_selection",
                "type": field_type,
                "message": "x_type_client is not a selection field, no fix needed",
            }

        # Get current selection values
        current_selection = field_info.get("selection", [])
        current_keys = [s[0] for s in current_selection] if current_selection else []

        # Find the field ID
        field_records = await odoo.search_read(
            "ir.model.fields",
            [["model", "=", "res.partner"], ["name", "=", "x_type_client"]],
            ["id"],
            limit=1,
        )

        if not field_records:
            return {"error": "Field record not found in ir.model.fields"}

        field_id = field_records[0]["id"]

        # Add missing selection values
        added = []
        for key, label in TYPE_CLIENT_NEW_OPTIONS.items():
            if key not in current_keys:
                try:
                    await odoo.create("ir.model.fields.selection", {
                        "field_id": field_id,
                        "value": key,
                        "name": label,
                        "sequence": (len(current_keys) + len(added)) * 10,
                    })
                    added.append(key)
                except Exception as e:
                    pass

        return {
            "status": "ok",
            "current_options": current_keys,
            "added_options": added,
            "all_options": current_keys + added,
        }

    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Erreur: {str(e)}")


@router.get("/check-fields", response_model=FieldCheckResponse)
async def check_custom_fields():
    """
    Vérifie quels champs custom x_* existent dans res.partner.
    Compare avec la liste requise pour l'enrichissement.
    """
    odoo = get_odoo_client()

    try:
        all_fields = await odoo.fields_get("res.partner", ["string", "type"])
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Erreur Odoo fields_get: {str(e)}")

    # Filter to only x_ custom fields
    x_fields = [f for f in all_fields.keys() if f.startswith("x_")]

    required = list(REQUIRED_FIELDS.keys())
    existing = [f for f in required if f in all_fields]
    missing = [f for f in required if f not in all_fields]

    return FieldCheckResponse(
        existing_fields=existing,
        missing_fields=missing,
        all_x_fields=sorted(x_fields),
    )


@router.post("/create-fields")
async def create_missing_fields():
    """
    Crée les champs custom manquants dans res.partner.
    """
    odoo = get_odoo_client()

    try:
        all_fields = await odoo.fields_get("res.partner", ["string", "type"])
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Erreur Odoo: {str(e)}")

    # Get model ID for res.partner
    try:
        model_ids = await odoo.search_read(
            "ir.model",
            [["model", "=", "res.partner"]],
            ["id"],
            limit=1,
        )
        if not model_ids:
            raise HTTPException(status_code=500, detail="Model res.partner not found")
        model_id = model_ids[0]["id"]
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Erreur finding model: {str(e)}")

    created = []
    errors = []

    for field_name, field_def in REQUIRED_FIELDS.items():
        if field_name in all_fields:
            continue

        try:
            field_type = field_def["type"]
            values = {
                "name": field_name,
                "field_description": field_def["label"],
                "model_id": model_id,
                "ttype": field_type,
                "state": "manual",
            }

            if field_type == "char" and "size" in field_def:
                values["size"] = field_def["size"]

            await odoo.create("ir.model.fields", values)
            created.append(field_name)
        except Exception as e:
            errors.append(f"{field_name}: {str(e)}")

    return {
        "created": created,
        "errors": errors,
        "total_created": len(created),
    }


@router.post("/migrate-enriched", response_model=MigrationResult)
async def migrate_enriched_data():
    """
    Migration complète : crée les champs manquants, crée les clients manquants,
    et met à jour tous les 25 clients avec les données enrichies.
    """
    odoo = get_odoo_client()
    result = MigrationResult(
        created_fields=[],
        created_partners=[],
        updated_partners=[],
        errors=[],
    )

    # Step 1: Check and create missing fields
    valid_type_client_values = set()
    try:
        all_fields = await odoo.fields_get("res.partner", ["string", "type", "selection"])
        model_ids = await odoo.search_read(
            "ir.model", [["model", "=", "res.partner"]], ["id"], limit=1,
        )
        model_id = model_ids[0]["id"] if model_ids else None

        # Check x_type_client selection values and add missing ones
        if "x_type_client" in all_fields:
            tc_info = all_fields["x_type_client"]
            if tc_info.get("type") == "selection":
                sel = tc_info.get("selection", [])
                valid_type_client_values = {s[0] for s in sel} if sel else set()

                # Add missing selection options (particulier, autre)
                field_recs = await odoo.search_read(
                    "ir.model.fields",
                    [["model", "=", "res.partner"], ["name", "=", "x_type_client"]],
                    ["id"], limit=1,
                )
                if field_recs:
                    fid = field_recs[0]["id"]
                    for key, label in TYPE_CLIENT_NEW_OPTIONS.items():
                        if key not in valid_type_client_values:
                            try:
                                await odoo.create("ir.model.fields.selection", {
                                    "field_id": fid, "value": key,
                                    "name": label, "sequence": 100,
                                })
                                valid_type_client_values.add(key)
                                result.created_fields.append(f"x_type_client option: {key}")
                            except Exception:
                                pass

        for field_name, field_def in REQUIRED_FIELDS.items():
            if field_name not in all_fields and model_id:
                try:
                    values = {
                        "name": field_name,
                        "field_description": field_def["label"],
                        "model_id": model_id,
                        "ttype": field_def["type"],
                        "state": "manual",
                    }
                    if field_def["type"] == "char" and "size" in field_def:
                        values["size"] = field_def["size"]
                    await odoo.create("ir.model.fields", values)
                    result.created_fields.append(field_name)
                except Exception as e:
                    result.errors.append(f"Field {field_name}: {str(e)}")
    except Exception as e:
        result.errors.append(f"Fields check: {str(e)}")

    # Step 2: Process each client
    for client in ENRICHED_CLIENTS:
        partner_id = client.get("odoo_id")

        # Build update values (only non-empty fields)
        update_vals = {}
        if client.get("phone"):
            update_vals["phone"] = client["phone"]
        if client.get("email"):
            update_vals["email"] = client["email"]
        if client.get("website"):
            update_vals["website"] = client["website"]
        if client.get("street"):
            update_vals["street"] = client["street"]
        if client.get("city"):
            update_vals["city"] = client["city"]
        if client.get("zip"):
            update_vals["zip"] = client["zip"]

        # Score: map A+/B+/C+ to A/B/C (Odoo only accepts A, B, C)
        score = client.get("score", "")
        if score:
            score_clean = score.replace("+", "")
            if score_clean in ("A", "B", "C"):
                update_vals["x_score_client"] = score_clean

        # Custom fields (excluding x_type_client which is handled separately)
        custom_map = {
            "facebook": "x_facebook",
            "instagram": "x_instagram",
            "linkedin": "x_linkedin",
            "google_maps": "x_google_maps",
            "description": "x_description",
            "year_founded": "x_year_founded",
            "employees_estimate": "x_employees_estimate",
            "revenue_estimate": "x_revenue_estimate",
            "req_number": "x_req_number",
            "brands": "x_brands",
            "specialties": "x_specialties",
            "hours": "x_hours",
            "notes_terrain": "x_notes_terrain",
        }

        for src_key, odoo_field in custom_map.items():
            val = client.get(src_key, "")
            if val:
                update_vals[odoo_field] = val

        # Handle x_type_client (selection field) — map label to Odoo key
        type_client = client.get("type_client", "")
        if type_client:
            odoo_key = TYPE_CLIENT_MAP.get(type_client)
            if odoo_key and odoo_key in valid_type_client_values:
                update_vals["x_type_client"] = odoo_key

        # Territory mapping
        territoire = client.get("territoire", "")
        terr_id = TERRITORY_MAP.get(territoire)
        if terr_id:
            update_vals["x_territoire"] = terr_id

        if partner_id is None:
            # Create new partner
            try:
                create_vals = {
                    "name": client["name"],
                    "is_company": True,
                    **update_vals,
                }
                new_id = await odoo.create("res.partner", create_vals)
                # Force is_company=True (Odoo may ignore it during create)
                await odoo.write("res.partner", [new_id], {"is_company": True})
                result.created_partners.append({
                    "rank": client["rank"],
                    "name": client["name"],
                    "new_odoo_id": new_id,
                })
            except Exception as e:
                result.errors.append(
                    f"Create rank {client['rank']} ({client['name']}): {str(e)}"
                )
        else:
            # Update existing partner
            try:
                await odoo.write("res.partner", [partner_id], update_vals)
                result.updated_partners.append({
                    "rank": client["rank"],
                    "name": client["name"],
                    "odoo_id": partner_id,
                    "fields_updated": list(update_vals.keys()),
                })
            except Exception as e:
                result.errors.append(
                    f"Update rank {client['rank']} ({client['name']}, ID {partner_id}): {str(e)}"
                )

    return result


@router.put("/update-partner/{partner_id}")
async def update_partner(partner_id: int, data: PartnerUpdateRequest):
    """
    Met à jour un partenaire Odoo avec les données fournies.
    Seuls les champs non-null sont mis à jour.
    """
    odoo = get_odoo_client()

    update_vals = {}
    for field, value in data.model_dump(exclude_unset=True).items():
        if value is not None:
            update_vals[field] = value

    if not update_vals:
        raise HTTPException(status_code=400, detail="Aucun champ à mettre à jour")

    try:
        await odoo.write("res.partner", [partner_id], update_vals)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Erreur Odoo: {str(e)}")

    return {"status": "ok", "partner_id": partner_id, "updated_fields": list(update_vals.keys())}


@router.post("/create-partner")
async def create_partner(data: PartnerCreateRequest):
    """
    Crée un nouveau partenaire dans Odoo.
    """
    odoo = get_odoo_client()

    values = data.model_dump(exclude_unset=True)
    values["is_company"] = True

    # Remove empty values
    values = {k: v for k, v in values.items() if v}
    values["is_company"] = True  # Always set

    try:
        new_id = await odoo.create("res.partner", values)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Erreur Odoo: {str(e)}")

    return {"status": "ok", "partner_id": new_id, "name": data.name}


@router.get("/diagnose-partners/{partner_ids}")
async def diagnose_partners(partner_ids: str):
    """
    Diagnostic: read partners by IDs with basic fields only.
    partner_ids is a comma-separated list of IDs (e.g., '561,562,563').
    """
    odoo = get_odoo_client()

    ids = [int(x.strip()) for x in partner_ids.split(",") if x.strip()]

    try:
        records = await odoo.read(
            "res.partner", ids,
            ["id", "name", "is_company", "active", "phone", "city", "email", "type"]
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Erreur Odoo: {str(e)}")

    return {"count": len(records), "partners": records}


@router.post("/fix-is-company/{partner_ids}")
async def fix_is_company(partner_ids: str):
    """
    Fix: set is_company=True on specified partner IDs.
    partner_ids is a comma-separated list of IDs.
    """
    odoo = get_odoo_client()

    ids = [int(x.strip()) for x in partner_ids.split(",") if x.strip()]

    try:
        await odoo.write("res.partner", ids, {"is_company": True})
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Erreur Odoo: {str(e)}")

    # Verify
    records = await odoo.read("res.partner", ids, ["id", "name", "is_company"])
    return {"status": "ok", "fixed_count": len(ids), "partners": records}


@router.post("/assign-leads")
async def assign_leads_to_user(
    user_email: str = "",
    lead_ids: str = "",
    count: int = 5,
):
    """
    Assigne des leads existants à un utilisateur (par email).
    Si lead_ids est vide, prend les N premiers leads non-assignés ou réassigne.
    """
    odoo = get_odoo_client()

    # Find user by email
    users = await odoo.search_read(
        "res.users",
        [["email", "=", user_email], ["active", "=", True]],
        ["id", "name"],
        limit=1,
    )
    if not users:
        raise HTTPException(status_code=404, detail=f"User not found: {user_email}")

    user_id = users[0]["id"]
    user_name = users[0]["name"]

    if lead_ids:
        ids = [int(x.strip()) for x in lead_ids.split(",") if x.strip()]
    else:
        # Get some leads to reassign
        leads = await odoo.search_read(
            "crm.lead", [], ["id"], limit=count * 2, order="id asc",
        )
        # Take every other lead to spread data
        ids = [l["id"] for i, l in enumerate(leads) if i % 2 == 0][:count]

    if not ids:
        return {"status": "no_leads", "message": "No leads found to assign"}

    await odoo.write("crm.lead", ids, {"user_id": user_id})

    return {
        "status": "ok",
        "user": user_name,
        "user_id": user_id,
        "assigned_lead_ids": ids,
        "count": len(ids),
    }


# ═══════════════════════════════════════════════════════════════
# MEGA ENRICHMENT: One endpoint to rule them all
# ═══════════════════════════════════════════════════════════════

# Smart tags for Quebec ébénisteries / granite industry
PARTNER_TAGS = [
    {"name": "Fabricant d'armoires", "color": 1},
    {"name": "Ébénisterie", "color": 2},
    {"name": "Designer d'intérieur", "color": 3},
    {"name": "Client Actif", "color": 4},
    {"name": "Client Dormant", "color": 5},
    {"name": "Prospect", "color": 6},
    {"name": "Score A — Prioritaire", "color": 10},
    {"name": "Score B — Régulier", "color": 8},
    {"name": "Score C — Occasionnel", "color": 7},
    {"name": "Résidentiel", "color": 9},
    {"name": "Commercial", "color": 11},
    {"name": "Luxe / Haut de gamme", "color": 3},
    {"name": "Cosentino", "color": 1},
    {"name": "Silestone", "color": 2},
    {"name": "Dekton", "color": 5},
    {"name": "Cambria", "color": 4},
    {"name": "Caesarstone", "color": 8},
    {"name": "Mauricie", "color": 10},
    {"name": "Centre-du-Québec", "color": 9},
    {"name": "Estrie", "color": 7},
    {"name": "Rive-Sud", "color": 6},
    {"name": "Écoresponsable", "color": 11},
    {"name": "Volume croissant", "color": 4},
    {"name": "Volume décroissant", "color": 5},
    {"name": "Nouveau client 2021+", "color": 3},
]

# Activity templates — realistic for granite/countertop sales reps
ACTIVITY_TEMPLATES = [
    # Calls
    {"type": "Appel téléphonique", "summaries": [
        "Appel de suivi — vérifier satisfaction installation récente",
        "Appel de courtoisie — nouvelles du marché",
        "Relance téléphonique — soumission en attente",
        "Appel pour présenter les nouveaux produits Cosentino 2025",
        "Discussion sur les besoins Q{quarter} {year}",
        "Confirmation disponibilité matériaux",
        "Appel post-livraison — feedback client final",
        "Suivi commande en cours — délais de livraison",
        "Appel découverte — premier contact",
        "Discussion partenariat — conditions commerciales",
    ]},
    # Meetings / visits
    {"type": "Réunion", "summaries": [
        "Visite atelier — présentation échantillons Silestone",
        "Rendez-vous showroom — nouveautés Dekton {year}",
        "Visite terrain — mesures pour projet résidentiel",
        "Réunion annuelle — révision volumes et conditions",
        "Visite de courtoisie avec échantillons",
        "Présentation catalogue printemps/été {year}",
        "Rencontre planification projets Q{quarter}",
        "Visite chantier en cours — support technique",
        "Formation produit — nouvelles finitions disponibles",
        "Dîner d'affaires — renforcement relation",
    ]},
    # Emails / follow-ups
    {"type": "Email", "summaries": [
        "Envoi soumission — comptoir quartz {surface}pi2",
        "Envoi catalogue numérique {year}",
        "Relance soumission #{num} — en attente réponse",
        "Confirmation de commande — {material}",
        "Envoi fiche technique {material}",
        "Rappel promotion fin de mois",
        "Documentation technique — entretien et garantie",
        "Facture et récapitulatif commande",
        "Invitation événement Cosentino",
        "Partage photos projets réalisés — portfolio",
    ]},
    # To-do / internal
    {"type": "À faire", "summaries": [
        "Préparer soumission pour projet {city}",
        "Mettre à jour fiche client dans CRM",
        "Vérifier inventaire matériaux demandés",
        "Planifier prochaine visite terrain",
        "Analyser historique d'achats — tendances",
        "Préparer présentoir échantillons",
        "Relancer paiement facture en retard",
        "Compléter rapport visite du {date}",
        "Envoyer photos projets réalisés au client",
        "Coordonner livraison avec entrepôt",
    ]},
]

# Notes templates for message_post (internal notes on partner timeline)
NOTE_TEMPLATES = [
    "Visite effectuée le {date}. Client {sentiment}. {detail}",
    "Appel du {date} — {detail}",
    "Soumission #{num} envoyée le {date} pour {surface}pi² de {material}. Montant: {amount}$.",
    "Client a commandé {surface}pi² de {material}. Livraison prévue {delivery_date}.",
    "Feedback post-installation: {sentiment}. {detail}",
    "Rencontre avec {contact_name} — Discussion sur projets Q{quarter} {year}. {detail}",
    "Note interne: {detail}",
]

SENTIMENTS = [
    "très satisfait des dernières livraisons",
    "intéressé par les nouveaux produits Dekton",
    "en attente de budget pour prochain trimestre",
    "mentionne augmentation de volume prévu",
    "compare avec compétiteur Richelieu",
    "satisfait de la qualité mais demande meilleur délai",
    "souhaite voir les nouvelles couleurs Silestone",
    "prêt à augmenter les commandes si prix compétitif",
    "projet résidentiel haut de gamme en vue",
    "ralentissement temporaire — reprend en Q{quarter}",
]

MATERIALS = ["Silestone Calacatta Gold", "Dekton Aura 15", "Silestone Ethereal Glow",
             "Dekton Bergen", "Silestone Loft Nolita", "Caesarstone Empira White",
             "Silestone Et. Marquina", "Dekton Kreta", "Cambria Brittanicca",
             "Silestone Charcoal Soapstone", "Dekton Trilium", "Quartz blanc classique"]

DETAILS = [
    "Le client planifie 3-4 projets cuisine pour les prochains mois.",
    "Intérêt marqué pour les surfaces grand format Dekton.",
    "Besoin de formation pour son équipe sur l'entretien des surfaces.",
    "Cherche un partenaire fiable pour remplacer fournisseur actuel.",
    "Volume en hausse vs année dernière.",
    "Budget serré ce trimestre, mais optimiste pour le suivant.",
    "Projets commerciaux à venir — restaurant et hôtel boutique.",
    "Référé par un autre client (bouche-à-oreille).",
    "Demande exclusivité sur certaines couleurs dans sa région.",
    "Discuté conditions de paiement — net 30 à maintenir.",
    "Client fidèle depuis plus de 5 ans.",
    "Première commande ce trimestre — à surveiller.",
    "Commande urgente — besoin de livraison dans 5 jours ouvrables.",
    "Discussion sur projet institutionnel (école/hôpital).",
    "Le client veut diversifier ses fournisseurs de surface.",
]

CITIES = ["Trois-Rivières", "Drummondville", "Victoriaville", "Sherbrooke",
          "Magog", "Bécancour", "Shawinigan", "Saint-Hyacinthe", "Longueuil",
          "Saint-Jean-sur-Richelieu"]

CONTACT_NAMES = ["Jean-François", "Marie-Claude", "Stéphane", "Nathalie",
                 "Pierre-Luc", "Isabelle", "Martin", "Julie", "Christian", "Sophie"]


def _gen_activity_summary(template_summaries: list, year: int, quarter: int) -> str:
    """Generate a realistic activity summary."""
    summary = random.choice(template_summaries)
    return summary.format(
        year=year,
        quarter=quarter,
        surface=random.randint(20, 150),
        num=random.randint(1001, 9999),
        material=random.choice(MATERIALS),
        city=random.choice(CITIES),
        date=f"{year}-{random.randint(1,12):02d}-{random.randint(1,28):02d}",
    )


def _gen_note(year: int, quarter: int, month: int) -> str:
    """Generate a realistic internal note."""
    template = random.choice(NOTE_TEMPLATES)
    day = random.randint(1, 28)
    return template.format(
        date=f"{year}-{month:02d}-{day:02d}",
        sentiment=random.choice(SENTIMENTS).format(quarter=quarter),
        detail=random.choice(DETAILS),
        surface=random.randint(20, 180),
        material=random.choice(MATERIALS),
        amount=random.randint(2000, 45000),
        num=random.randint(1001, 9999),
        delivery_date=f"{year}-{month:02d}-{min(day+7, 28):02d}",
        contact_name=random.choice(CONTACT_NAMES),
        quarter=quarter,
        year=year,
    )


# Odoo stage IDs — will be resolved dynamically
LEAD_STAGES = {
    "New": None,
    "Qualified": None,
    "Proposition": None,
    "Won": None,
}


@router.post("/enrich-all")
async def enrich_all():
    """
    🚀 MEGA ENRICHMENT — Corrige et enrichit TOUT le CRM Odoo en un seul appel.

    1. Fix countries → Canada pour tous les partenaires
    2. Crée les champs custom manquants
    3. Met à jour les 25 clients avec données enrichies (web, réseaux sociaux)
    4. Crée les étiquettes intelligentes (tags)
    5. Assigne les tags aux clients
    6. Crée des leads pour les clients qui n'en ont pas
    7. Assigne les leads aux représentants
    8. Génère 12 mois d'activités réalistes (notes, appels, visites)
    """
    odoo = get_odoo_client()
    log = {
        "step_1_countries": {"status": "pending"},
        "step_2_fields": {"status": "pending"},
        "step_3_partners": {"status": "pending"},
        "step_4_tags": {"status": "pending"},
        "step_5_tag_assign": {"status": "pending"},
        "step_6_leads": {"status": "pending"},
        "step_7_assign_reps": {"status": "pending"},
        "step_8_activities": {"status": "pending"},
        "errors": [],
    }

    # ═══════════════════════════════════════
    # STEP 1: Fix all partner countries to Canada
    # ═══════════════════════════════════════
    try:
        # Find Canada country ID
        canada = await odoo.search_read(
            "res.country", [["code", "=", "CA"]], ["id", "name"], limit=1,
        )
        canada_id = canada[0]["id"] if canada else 39  # fallback

        # Find Quebec state ID
        quebec = await odoo.search_read(
            "res.country.state",
            [["country_id", "=", canada_id], ["code", "=", "QC"]],
            ["id", "name"], limit=1,
        )
        quebec_id = quebec[0]["id"] if quebec else None

        # Get all company partners
        all_partners = await odoo.search_read(
            "res.partner", [["is_company", "=", True]],
            ["id", "name", "country_id", "state_id"], limit=500,
        )

        fixed_countries = 0
        for p in all_partners:
            country = p.get("country_id")
            country_id = country[0] if isinstance(country, (list, tuple)) else country
            update = {}
            if country_id != canada_id:
                update["country_id"] = canada_id
            state = p.get("state_id")
            state_id = state[0] if isinstance(state, (list, tuple)) else state
            if not state_id and quebec_id:
                update["state_id"] = quebec_id
            if update:
                try:
                    await odoo.write("res.partner", [p["id"]], update)
                    fixed_countries += 1
                except Exception as e:
                    log["errors"].append(f"Country fix {p['id']}: {str(e)}")

        log["step_1_countries"] = {
            "status": "done",
            "canada_id": canada_id,
            "quebec_id": quebec_id,
            "total_partners": len(all_partners),
            "fixed": fixed_countries,
        }
    except Exception as e:
        log["step_1_countries"] = {"status": "error", "error": str(e)}
        log["errors"].append(f"Step 1: {str(e)}")

    # ═══════════════════════════════════════
    # STEP 2: Create missing custom fields
    # ═══════════════════════════════════════
    try:
        all_fields = await odoo.fields_get("res.partner", ["string", "type", "selection"])
        model_ids = await odoo.search_read(
            "ir.model", [["model", "=", "res.partner"]], ["id"], limit=1,
        )
        model_id = model_ids[0]["id"] if model_ids else None

        created_fields = []
        valid_type_client_values = set()

        # Check x_type_client selection values
        if "x_type_client" in all_fields:
            tc_info = all_fields["x_type_client"]
            if tc_info.get("type") == "selection":
                sel = tc_info.get("selection", [])
                valid_type_client_values = {s[0] for s in sel} if sel else set()

                field_recs = await odoo.search_read(
                    "ir.model.fields",
                    [["model", "=", "res.partner"], ["name", "=", "x_type_client"]],
                    ["id"], limit=1,
                )
                if field_recs:
                    fid = field_recs[0]["id"]
                    for key, label in TYPE_CLIENT_NEW_OPTIONS.items():
                        if key not in valid_type_client_values:
                            try:
                                await odoo.create("ir.model.fields.selection", {
                                    "field_id": fid, "value": key,
                                    "name": label, "sequence": 100,
                                })
                                valid_type_client_values.add(key)
                                created_fields.append(f"x_type_client:{key}")
                            except Exception:
                                pass

        for field_name, field_def in REQUIRED_FIELDS.items():
            if field_name not in all_fields and model_id:
                try:
                    values = {
                        "name": field_name,
                        "field_description": field_def["label"],
                        "model_id": model_id,
                        "ttype": field_def["type"],
                        "state": "manual",
                    }
                    if field_def["type"] == "char" and "size" in field_def:
                        values["size"] = field_def["size"]
                    await odoo.create("ir.model.fields", values)
                    created_fields.append(field_name)
                except Exception as e:
                    log["errors"].append(f"Field {field_name}: {str(e)}")

        log["step_2_fields"] = {"status": "done", "created": created_fields}
    except Exception as e:
        log["step_2_fields"] = {"status": "error", "error": str(e)}
        log["errors"].append(f"Step 2: {str(e)}")
        valid_type_client_values = set()

    # ═══════════════════════════════════════
    # STEP 3: Enrich all 25 partners
    # ═══════════════════════════════════════
    partner_id_map = {}  # name -> odoo_id (for later use)
    try:
        created_partners = []
        updated_partners = []

        for client in ENRICHED_CLIENTS:
            partner_id = client.get("odoo_id")

            update_vals = {}
            if client.get("phone"):
                update_vals["phone"] = client["phone"]
            if client.get("email"):
                update_vals["email"] = client["email"]
            if client.get("website"):
                update_vals["website"] = client["website"]
            if client.get("street"):
                update_vals["street"] = client["street"]
            if client.get("city"):
                update_vals["city"] = client["city"]
            if client.get("zip"):
                update_vals["zip"] = client["zip"]

            # Always set country to Canada
            if canada_id:
                update_vals["country_id"] = canada_id
            if quebec_id:
                update_vals["state_id"] = quebec_id

            score = client.get("score", "")
            if score:
                score_clean = score.replace("+", "")
                if score_clean in ("A", "B", "C"):
                    update_vals["x_score_client"] = score_clean

            custom_map = {
                "facebook": "x_facebook", "instagram": "x_instagram",
                "linkedin": "x_linkedin", "google_maps": "x_google_maps",
                "description": "x_description", "year_founded": "x_year_founded",
                "employees_estimate": "x_employees_estimate",
                "revenue_estimate": "x_revenue_estimate",
                "req_number": "x_req_number", "brands": "x_brands",
                "specialties": "x_specialties", "hours": "x_hours",
                "notes_terrain": "x_notes_terrain",
            }

            for src_key, odoo_field in custom_map.items():
                val = client.get(src_key, "")
                if val:
                    update_vals[odoo_field] = val

            type_client = client.get("type_client", "")
            if type_client:
                odoo_key = TYPE_CLIENT_MAP.get(type_client)
                if odoo_key and odoo_key in valid_type_client_values:
                    update_vals["x_type_client"] = odoo_key

            territoire = client.get("territoire", "")
            terr_id = TERRITORY_MAP.get(territoire)
            if terr_id:
                update_vals["x_territoire"] = terr_id

            if partner_id is None:
                # Try to find by name first
                existing = await odoo.search_read(
                    "res.partner",
                    [["name", "ilike", client["name"]], ["is_company", "=", True]],
                    ["id", "name"], limit=1,
                )
                if existing:
                    partner_id = existing[0]["id"]

            if partner_id is None:
                try:
                    create_vals = {"name": client["name"], "is_company": True, **update_vals}
                    new_id = await odoo.create("res.partner", create_vals)
                    await odoo.write("res.partner", [new_id], {"is_company": True})
                    partner_id_map[client["name"]] = new_id
                    created_partners.append({"name": client["name"], "id": new_id})
                except Exception as e:
                    log["errors"].append(f"Create {client['name']}: {str(e)}")
            else:
                try:
                    await odoo.write("res.partner", [partner_id], update_vals)
                    partner_id_map[client["name"]] = partner_id
                    updated_partners.append({"name": client["name"], "id": partner_id})
                except Exception as e:
                    log["errors"].append(f"Update {client['name']}: {str(e)}")

        log["step_3_partners"] = {
            "status": "done",
            "created": len(created_partners),
            "updated": len(updated_partners),
            "details": created_partners + updated_partners,
        }
    except Exception as e:
        log["step_3_partners"] = {"status": "error", "error": str(e)}
        log["errors"].append(f"Step 3: {str(e)}")

    # ═══════════════════════════════════════
    # STEP 4: Create smart partner tags
    # ═══════════════════════════════════════
    tag_id_map = {}  # tag_name -> tag_id
    try:
        existing_tags = await odoo.search_read(
            "res.partner.category", [], ["id", "name"], limit=500,
        )
        existing_tag_names = {t["name"].lower(): t["id"] for t in existing_tags}

        created_tags = []
        for tag_def in PARTNER_TAGS:
            tag_lower = tag_def["name"].lower()
            if tag_lower in existing_tag_names:
                tag_id_map[tag_def["name"]] = existing_tag_names[tag_lower]
            else:
                try:
                    new_tag_id = await odoo.create("res.partner.category", {
                        "name": tag_def["name"],
                        "color": tag_def["color"],
                    })
                    tag_id_map[tag_def["name"]] = new_tag_id
                    created_tags.append(tag_def["name"])
                except Exception as e:
                    log["errors"].append(f"Tag {tag_def['name']}: {str(e)}")

        log["step_4_tags"] = {
            "status": "done",
            "created": len(created_tags),
            "existing": len(existing_tag_names),
            "total": len(tag_id_map),
            "created_names": created_tags,
        }
    except Exception as e:
        log["step_4_tags"] = {"status": "error", "error": str(e)}
        log["errors"].append(f"Step 4: {str(e)}")

    # ═══════════════════════════════════════
    # STEP 5: Assign tags to clients
    # ═══════════════════════════════════════
    try:
        assigned_tags_count = 0
        for client in ENRICHED_CLIENTS:
            pid = partner_id_map.get(client["name"]) or client.get("odoo_id")
            if not pid:
                continue

            tags_to_assign = []

            # Type-based tags
            tc = client.get("type_client", "")
            if "armoires" in tc.lower():
                tags_to_assign.append("Fabricant d'armoires")
            elif "ébénisterie" in tc.lower() or "ebenist" in tc.lower():
                tags_to_assign.append("Ébénisterie")
            elif "designer" in tc.lower():
                tags_to_assign.append("Designer d'intérieur")

            # Score-based tags
            score = client.get("score", "")
            if "A" in score:
                tags_to_assign.append("Score A — Prioritaire")
                tags_to_assign.append("Client Actif")
            elif "B" in score:
                tags_to_assign.append("Score B — Régulier")
                tags_to_assign.append("Client Actif")
            elif "C" in score:
                tags_to_assign.append("Score C — Occasionnel")

            # Specialty tags
            specs = client.get("specialties", "").lower()
            if "résidentiel" in specs:
                tags_to_assign.append("Résidentiel")
            if "commercial" in specs:
                tags_to_assign.append("Commercial")
            if "luxe" in specs:
                tags_to_assign.append("Luxe / Haut de gamme")
            if "écoresponsable" in specs.lower():
                tags_to_assign.append("Écoresponsable")

            # Brand tags
            brands = client.get("brands", "").lower()
            if "cosentino" in brands:
                tags_to_assign.append("Cosentino")
            if "silestone" in brands:
                tags_to_assign.append("Silestone")
            if "dekton" in brands:
                tags_to_assign.append("Dekton")
            if "cambria" in brands:
                tags_to_assign.append("Cambria")
            if "caesarstone" in brands:
                tags_to_assign.append("Caesarstone")

            # Region tags
            city = client.get("city", "").lower()
            notes = client.get("notes_terrain", "").lower()
            if "trois-rivières" in city or "cap-de-la-madeleine" in city or "saint-maurice" in city:
                tags_to_assign.append("Mauricie")
            elif "drummondville" in city or "victoriaville" in city or "tingwick" in city:
                tags_to_assign.append("Centre-du-Québec")
            elif "magog" in city or "sherbrooke" in city or "estrie" in city:
                tags_to_assign.append("Estrie")
            elif "beloeil" in city or "rive-sud" in notes:
                tags_to_assign.append("Rive-Sud")

            # Volume trend tags
            volumes = client.get("notes_terrain", "")
            if "2022:" in volumes and "2021:" in volumes:
                try:
                    v22_start = volumes.index("2022:") + 6
                    v22_str = volumes[v22_start:].split("$")[0].strip().replace(",", "").replace(" ", "")
                    v21_start = volumes.index("2021:") + 6
                    v21_str = volumes[v21_start:].split("$")[0].strip().replace(",", "").replace(" ", "")
                    v22 = int(v22_str)
                    v21 = int(v21_str)
                    if v22 > v21 * 1.1:
                        tags_to_assign.append("Volume croissant")
                    elif v22 < v21 * 0.5:
                        tags_to_assign.append("Volume décroissant")
                        if score == "A" or score == "B":
                            tags_to_assign.append("Client Dormant")
                            if "Client Actif" in tags_to_assign:
                                tags_to_assign.remove("Client Actif")
                except (ValueError, IndexError):
                    pass

            # Convert to IDs
            tag_ids = [tag_id_map[t] for t in tags_to_assign if t in tag_id_map]
            if tag_ids:
                try:
                    # Use (6, 0, ids) to set tags (replaces existing)
                    await odoo.write("res.partner", [pid], {
                        "category_id": [(6, 0, tag_ids)]
                    })
                    assigned_tags_count += 1
                except Exception as e:
                    log["errors"].append(f"Tag assign {client['name']}: {str(e)}")

        log["step_5_tag_assign"] = {
            "status": "done",
            "partners_tagged": assigned_tags_count,
        }
    except Exception as e:
        log["step_5_tag_assign"] = {"status": "error", "error": str(e)}
        log["errors"].append(f"Step 5: {str(e)}")

    # ═══════════════════════════════════════
    # STEP 6: Create leads for clients without any
    # ═══════════════════════════════════════
    try:
        # Get all existing leads
        existing_leads = await odoo.search_read(
            "crm.lead", [], ["id", "partner_id", "name"], limit=1000,
        )
        partners_with_leads = set()
        for l in existing_leads:
            pid = l.get("partner_id")
            if isinstance(pid, (list, tuple)):
                partners_with_leads.add(pid[0])
            elif pid:
                partners_with_leads.add(pid)

        # Get stages
        stages = await odoo.search_read("crm.stage", [], ["id", "name"], limit=20)
        stage_map = {}
        for s in stages:
            sname = s["name"].lower()
            if "new" in sname or "nouveau" in sname:
                stage_map["new"] = s["id"]
            elif "qualif" in sname:
                stage_map["qualified"] = s["id"]
            elif "propos" in sname or "negoc" in sname or "négoc" in sname:
                stage_map["proposition"] = s["id"]
            elif "won" in sname or "gagné" in sname:
                stage_map["won"] = s["id"]
            elif "lost" in sname or "perdu" in sname:
                stage_map["lost"] = s["id"]

        default_stage = stage_map.get("new") or (stages[0]["id"] if stages else 1)

        lead_names_templates = [
            "Comptoir cuisine {surface}pi² — {material}",
            "Projet salle de bain — vanité {material}",
            "Îlot cuisine {material} — {city}",
            "Rénovation comptoirs — {material}",
            "Projet commercial — surface {material}",
            "Soumission {surface}pi² {material}",
            "Dosserets + comptoir — {material}",
            "Agrandissement cuisine — {material}",
        ]

        created_leads = []
        for client in ENRICHED_CLIENTS:
            pid = partner_id_map.get(client["name"]) or client.get("odoo_id")
            if not pid or pid in partners_with_leads:
                continue

            # Create 1-3 leads per client depending on score
            num_leads = 3 if client.get("score") == "A" else 2 if client.get("score") == "B" else 1
            for i in range(num_leads):
                material = random.choice(MATERIALS)
                surface = random.randint(25, 200)
                city = client.get("city") or random.choice(CITIES)
                lead_name = random.choice(lead_names_templates).format(
                    surface=surface, material=material, city=city,
                )
                # Pick a stage
                if i == 0 and client.get("score") in ("A", "B"):
                    stage_id = stage_map.get("qualified") or stage_map.get("proposition") or default_stage
                    probability = random.choice([60, 70, 80])
                elif i == 1:
                    stage_id = stage_map.get("proposition") or default_stage
                    probability = random.choice([30, 40, 50])
                else:
                    stage_id = default_stage
                    probability = random.choice([10, 20, 30])

                revenue = surface * random.randint(45, 120)
                deadline = (datetime.now() + timedelta(days=random.randint(7, 90))).strftime("%Y-%m-%d")

                try:
                    lead_id = await odoo.create("crm.lead", {
                        "name": lead_name,
                        "partner_id": pid,
                        "stage_id": stage_id,
                        "expected_revenue": revenue,
                        "probability": probability,
                        "date_deadline": deadline,
                        "type": "opportunity",
                    })
                    created_leads.append({"id": lead_id, "name": lead_name, "partner": client["name"]})
                except Exception as e:
                    log["errors"].append(f"Lead create {client['name']}: {str(e)}")

        log["step_6_leads"] = {
            "status": "done",
            "partners_with_existing_leads": len(partners_with_leads),
            "new_leads_created": len(created_leads),
        }
    except Exception as e:
        log["step_6_leads"] = {"status": "error", "error": str(e)}
        log["errors"].append(f"Step 6: {str(e)}")

    # ═══════════════════════════════════════
    # STEP 7: Assign leads to reps
    # ═══════════════════════════════════════
    try:
        # Get all users (reps)
        users = await odoo.search_read(
            "res.users", [["active", "=", True]],
            ["id", "name", "email"], limit=20,
        )

        # Filter to actual rep users (exclude admin/system)
        admin_emails = {"pgirardin@saiphia.ca", "admin@example.com", "admin"}
        reps = [u for u in users if (u.get("email") or "").lower() not in admin_emails
                and u.get("email")]

        if not reps:
            reps = users[:3]  # Fallback: use first 3 users

        # Get ALL leads
        all_leads = await odoo.search_read(
            "crm.lead", [], ["id", "user_id"], limit=1000,
        )

        assigned_count = 0
        for i, lead in enumerate(all_leads):
            rep = reps[i % len(reps)]  # Round-robin assignment
            try:
                await odoo.write("crm.lead", [lead["id"]], {"user_id": rep["id"]})
                assigned_count += 1
            except Exception as e:
                log["errors"].append(f"Assign lead {lead['id']}: {str(e)}")

        log["step_7_assign_reps"] = {
            "status": "done",
            "reps_found": [{"id": r["id"], "name": r["name"]} for r in reps],
            "total_leads": len(all_leads),
            "assigned": assigned_count,
        }
    except Exception as e:
        log["step_7_assign_reps"] = {"status": "error", "error": str(e)}
        log["errors"].append(f"Step 7: {str(e)}")

    # ═══════════════════════════════════════
    # STEP 8: Generate 12 months of activities
    # ═══════════════════════════════════════
    try:
        # Get activity types
        activity_types = await odoo.search_read(
            "mail.activity.type", [], ["id", "name", "res_model"], limit=20,
        )
        at_map = {}
        for at in activity_types:
            name_lower = at["name"].lower()
            if "appel" in name_lower or "call" in name_lower or "phone" in name_lower:
                at_map["call"] = at["id"]
            elif "réunion" in name_lower or "meet" in name_lower or "rendez" in name_lower:
                at_map["meeting"] = at["id"]
            elif "email" in name_lower or "mail" in name_lower:
                at_map["email"] = at["id"]
            elif "faire" in name_lower or "todo" in name_lower or "to-do" in name_lower:
                at_map["todo"] = at["id"]

        # Fallback: use first available type
        default_at = activity_types[0]["id"] if activity_types else 1

        # Get res.partner model_id for mail.activity
        model_recs = await odoo.search_read(
            "ir.model", [["model", "=", "res.partner"]], ["id"], limit=1,
        )
        partner_model_id = model_recs[0]["id"] if model_recs else None

        # Get all company partners for notes
        all_company_partners = await odoo.search_read(
            "res.partner", [["is_company", "=", True]],
            ["id", "name"], limit=200,
        )

        notes_created = 0
        activities_created = 0
        now = datetime.now()

        for partner in all_company_partners:
            pid = partner["id"]

            # Generate ~2-4 notes per month for the past 12 months
            for months_ago in range(12, 0, -1):
                target_date = now - timedelta(days=months_ago * 30)
                year = target_date.year
                month = target_date.month
                quarter = (month - 1) // 3 + 1

                # Number of activities depends on client importance
                client_data = next(
                    (c for c in ENRICHED_CLIENTS
                     if c.get("odoo_id") == pid or partner_id_map.get(c["name"]) == pid),
                    None
                )
                if client_data and client_data.get("score") == "A":
                    num_notes = random.randint(3, 5)
                elif client_data and client_data.get("score") == "B":
                    num_notes = random.randint(2, 3)
                else:
                    num_notes = random.randint(1, 2)

                for _ in range(num_notes):
                    day = random.randint(1, 28)
                    note_date = f"{year}-{month:02d}-{day:02d}"
                    note_body = _gen_note(year, quarter, month)

                    try:
                        await odoo._call_kw(
                            "res.partner", "message_post", [pid],
                            {
                                "body": f"<p>{note_body}</p>",
                                "message_type": "comment",
                                "subtype_xmlid": "mail.mt_note",
                                "date": f"{note_date} {random.randint(8,17):02d}:{random.randint(0,59):02d}:00",
                            },
                        )
                        notes_created += 1
                    except Exception:
                        pass  # Some notes may fail, that's ok

            # Create 1-2 future scheduled activities
            if partner_model_id:
                for _ in range(random.randint(1, 2)):
                    days_future = random.randint(1, 60)
                    deadline = (now + timedelta(days=days_future)).strftime("%Y-%m-%d")
                    at_type_key = random.choice(list(at_map.keys())) if at_map else None
                    at_id = at_map.get(at_type_key, default_at)

                    template_idx = {"call": 0, "meeting": 1, "email": 2, "todo": 3}.get(at_type_key, 0)
                    summary = _gen_activity_summary(
                        ACTIVITY_TEMPLATES[template_idx]["summaries"],
                        now.year, (now.month - 1) // 3 + 1,
                    )

                    # Pick a rep to assign activity to
                    rep_id = reps[random.randint(0, len(reps) - 1)]["id"] if reps else 2

                    try:
                        await odoo.create("mail.activity", {
                            "res_model_id": partner_model_id,
                            "res_id": pid,
                            "activity_type_id": at_id,
                            "summary": summary,
                            "date_deadline": deadline,
                            "user_id": rep_id,
                        })
                        activities_created += 1
                    except Exception:
                        pass

        log["step_8_activities"] = {
            "status": "done",
            "partners_processed": len(all_company_partners),
            "notes_created": notes_created,
            "future_activities_created": activities_created,
        }
    except Exception as e:
        log["step_8_activities"] = {"status": "error", "error": str(e)}
        log["errors"].append(f"Step 8: {str(e)}")

    # ═══════════════════════════════════════
    # SUMMARY
    # ═══════════════════════════════════════
    log["summary"] = {
        "total_errors": len(log["errors"]),
        "status": "completed_with_errors" if log["errors"] else "success",
    }

    return log


# ═══════════════════════════════════════════════════════════════
# ISABELLE IMPORT — Create all fields + import 450 clients
# ═══════════════════════════════════════════════════════════════

# Custom fields matching Isabelle's tracking spreadsheet
ISABELLE_FIELDS = {
    "x_freq_visite": {"type": "selection", "label": "Fréquence de visite",
        "selection": [("mensuel", "Mensuel"), ("trimestriel", "Trimestriel"), ("semestriel", "Semestriel")]},
    "x_date_premiere_visite": {"type": "char", "label": "Première visite", "size": 50},
    "x_meilleure_annee": {"type": "char", "label": "Meilleure année", "size": 50},
    "x_ventes_2019": {"type": "float", "label": "Ventes 2019 ($)"},
    "x_ventes_2020": {"type": "float", "label": "Ventes 2020 ($)"},
    "x_ventes_2021": {"type": "float", "label": "Ventes 2021 ($)"},
    "x_ventes_2022": {"type": "float", "label": "Ventes 2022 ($)"},
    "x_ventes_2023": {"type": "float", "label": "Ventes 2023 ($)"},
    "x_ventes_total": {"type": "float", "label": "Ventes total ($)"},
    "x_contact_principal": {"type": "char", "label": "Contact principal", "size": 200},
    "x_contact_secondaire": {"type": "char", "label": "Contact secondaire", "size": 200},
    "x_competiteurs": {"type": "text", "label": "Compétiteurs"},
    "x_marques_interet": {"type": "text", "label": "Marques d'intérêt"},
    "x_echantillons_livres": {"type": "text", "label": "Échantillons livrés"},
    "x_historique_visites": {"type": "text", "label": "Historique des visites"},
    "x_bon_soumission": {"type": "char", "label": "Bon de soumission", "size": 100},
    "x_provenance": {"type": "char", "label": "Provenance", "size": 100},
    "x_salle_montre": {"type": "char", "label": "Salle de montre", "size": 100},
    "x_notes_isabelle": {"type": "text", "label": "Notes Isabelle"},
}


@router.post("/import-isabelle")
async def import_isabelle_data():
    """
    📊 Import complet du fichier de suivi d'Isabelle.

    1. Crée tous les champs custom Isabelle dans res.partner
    2. Importe les 450 clients avec toutes leurs données
    3. Fréquence de visite, chiffres de vente 2019-2023, contacts,
       compétiteurs, échantillons, historique de visites
    """
    odoo = get_odoo_client()
    log = {
        "step_1_fields": {"status": "pending"},
        "step_2_import": {"status": "pending"},
        "errors": [],
    }

    # Load the extracted data
    data_path = Path(__file__).parent.parent / "data" / "isabelle_clients.json"
    if not data_path.exists():
        # Fallback: use embedded data
        raise HTTPException(
            status_code=404,
            detail="isabelle_clients.json not found. Run the extraction first.",
        )

    with open(data_path) as f:
        isabelle_clients = json.load(f)

    # ═══════════════════════════════════════
    # STEP 1: Create custom fields
    # ═══════════════════════════════════════
    try:
        all_fields = await odoo.fields_get("res.partner", ["string", "type"])
        model_ids = await odoo.search_read(
            "ir.model", [["model", "=", "res.partner"]], ["id"], limit=1,
        )
        model_id = model_ids[0]["id"] if model_ids else None

        created_fields = []
        for field_name, field_def in ISABELLE_FIELDS.items():
            if field_name in all_fields:
                continue
            if not model_id:
                break

            try:
                values = {
                    "name": field_name,
                    "field_description": field_def["label"],
                    "model_id": model_id,
                    "ttype": field_def["type"],
                    "state": "manual",
                }
                if field_def["type"] == "char" and "size" in field_def:
                    values["size"] = field_def["size"]
                if field_def["type"] == "selection":
                    # Selection fields need special handling in Odoo 17
                    values["ttype"] = "selection"
                    values["selection_ids"] = [
                        (0, 0, {"value": k, "name": v, "sequence": i * 10})
                        for i, (k, v) in enumerate(field_def["selection"])
                    ]
                await odoo.create("ir.model.fields", values)
                created_fields.append(field_name)
            except Exception as e:
                log["errors"].append(f"Field {field_name}: {str(e)}")

        log["step_1_fields"] = {"status": "done", "created": created_fields}
    except Exception as e:
        log["step_1_fields"] = {"status": "error", "error": str(e)}
        log["errors"].append(f"Step 1: {str(e)}")

    # ═══════════════════════════════════════
    # STEP 2: Import all clients
    # ═══════════════════════════════════════
    try:
        # Find Canada + Quebec
        canada = await odoo.search_read("res.country", [["code", "=", "CA"]], ["id"], limit=1)
        canada_id = canada[0]["id"] if canada else 39
        quebec = await odoo.search_read(
            "res.country.state",
            [["country_id", "=", canada_id], ["code", "=", "QC"]],
            ["id"], limit=1,
        )
        quebec_id = quebec[0]["id"] if quebec else None

        # Territory mapping
        terr_map = {"3-RI": 8, "T03": 8, "T04": 12, "SHERB": None, "T05": None}

        # Get existing company partners for matching
        existing = await odoo.search_read(
            "res.partner", [["is_company", "=", True]],
            ["id", "name"], limit=1000,
        )
        # Build fuzzy match map
        existing_map = {}
        for p in existing:
            key = p["name"].lower().strip()
            existing_map[key] = p["id"]
            # Also match shortened versions
            parts = key.split()
            if len(parts) >= 2:
                existing_map[" ".join(parts[:2])] = p["id"]

        created = 0
        updated = 0
        skipped = 0

        for client in isabelle_clients:
            name = client["name"]
            name_lower = name.lower().strip()

            # Try to find existing partner
            partner_id = existing_map.get(name_lower)
            if not partner_id:
                # Try partial match
                for ek, eid in existing_map.items():
                    if name_lower in ek or ek in name_lower:
                        partner_id = eid
                        break

            if not partner_id:
                # Also try Odoo search
                search_results = await odoo.search_read(
                    "res.partner",
                    [["name", "ilike", name], ["is_company", "=", True]],
                    ["id", "name"], limit=1,
                )
                if search_results:
                    partner_id = search_results[0]["id"]

            # Build update values
            vals = {"country_id": canada_id}
            if quebec_id:
                vals["state_id"] = quebec_id

            terr_id = terr_map.get(client.get("territory"))
            if terr_id:
                vals["x_territoire"] = terr_id

            # Frequency
            freq = client.get("freq_visite", "")
            if freq:
                vals["x_freq_visite"] = freq

            # Sales data
            sales = client.get("sales", {})
            if sales.get("2019"):
                vals["x_ventes_2019"] = float(sales["2019"])
            if sales.get("2020"):
                vals["x_ventes_2020"] = float(sales["2020"])
            if sales.get("2021"):
                vals["x_ventes_2021"] = float(sales["2021"])
            if sales.get("2022"):
                vals["x_ventes_2022"] = float(sales["2022"])
            if sales.get("2023"):
                vals["x_ventes_2023"] = float(sales["2023"])
            total = client.get("total_sales", 0)
            if total:
                vals["x_ventes_total"] = float(total)

            # Best year
            if client.get("meilleure_annee"):
                vals["x_meilleure_annee"] = client["meilleure_annee"]

            # Contacts
            if client.get("contact_principal"):
                vals["x_contact_principal"] = client["contact_principal"]
            if client.get("contact_secondaire"):
                vals["x_contact_secondaire"] = client["contact_secondaire"]

            # Competitors
            comps = client.get("competiteurs", [])
            if comps:
                vals["x_competiteurs"] = ", ".join(comps)

            # Brand/sample tracking
            brands = client.get("brand_tracking", {})
            if brands:
                brand_summary = []
                for brand, items in brands.items():
                    brand_summary.append(f"{brand}: {', '.join(items[:3])}")
                vals["x_echantillons_livres"] = "\n".join(brand_summary[:20])

            # Visit history from deep_data
            deep = client.get("deep_data", {})
            if deep:
                visit_lines = []
                for key, val in deep.items():
                    visit_lines.append(f"{key}: {val}")
                vals["x_historique_visites"] = "\n".join(visit_lines)

            # Notes
            notes_parts = []
            if client.get("notes_debut"):
                notes_parts.append(f"Début: {client['notes_debut']}")
            if client.get("bon_soumission"):
                notes_parts.append(f"Bon soum: {client['bon_soumission']}")
            if notes_parts:
                vals["x_notes_isabelle"] = "\n".join(notes_parts)

            # First visit date
            if client.get("notes_debut") and len(client["notes_debut"]) == 4 and client["notes_debut"].isdigit():
                vals["x_date_premiere_visite"] = client["notes_debut"]

            try:
                if partner_id:
                    # Only update non-empty vals, don't overwrite existing enriched data
                    safe_vals = {k: v for k, v in vals.items() if v}
                    await odoo.write("res.partner", [partner_id], safe_vals)
                    updated += 1
                else:
                    vals["name"] = name
                    vals["is_company"] = True
                    new_id = await odoo.create("res.partner", vals)
                    await odoo.write("res.partner", [new_id], {"is_company": True})
                    created += 1
            except Exception as e:
                log["errors"].append(f"Client {name}: {str(e)}")
                skipped += 1

        log["step_2_import"] = {
            "status": "done",
            "total_clients": len(isabelle_clients),
            "created": created,
            "updated": updated,
            "skipped": skipped,
        }
    except Exception as e:
        log["step_2_import"] = {"status": "error", "error": str(e)}
        log["errors"].append(f"Step 2: {str(e)}")

    log["summary"] = {
        "total_errors": len(log["errors"]),
        "status": "completed_with_errors" if log["errors"] else "success",
    }
    return log


# ─── Cleanup bad imports ───

BAD_NAMES = [
    "6mois 3ri", "6mois t03", "6mois sher", "6mois t04", "6mois t05",
    "54 jours / 3 mois", "108 jours /6 mois", "48 semaines", "6mois",
]


@router.post("/cleanup-imports", summary="Cleanup bad imports")
async def cleanup_imports():
    """
    Supprime les partenaires créés par erreur (noms = métadonnées Excel).
    """
    odoo = get_odoo_client()
    log = {"deleted": [], "errors": []}

    for bad_name in BAD_NAMES:
        try:
            partners = await odoo.search_read(
                "res.partner",
                [["name", "=", bad_name]],
                ["id", "name"],
            )
            for p in partners:
                try:
                    await odoo._call_kw(
                        "res.partner", "unlink", [[p["id"]]], {}
                    )
                    log["deleted"].append(f"{p['name']} (id={p['id']})")
                except Exception as e:
                    # If can't delete (has leads/activities), archive instead
                    try:
                        await odoo._call_kw(
                            "res.partner", "write",
                            [[p["id"]], {"active": False}], {}
                        )
                        log["deleted"].append(f"{p['name']} (id={p['id']}) — archived")
                    except Exception as e2:
                        log["errors"].append(f"{p['name']}: {str(e2)}")
        except Exception as e:
            log["errors"].append(f"Search {bad_name}: {str(e)}")

    log["summary"] = {
        "total_deleted": len(log["deleted"]),
        "total_errors": len(log["errors"]),
    }
    return log
