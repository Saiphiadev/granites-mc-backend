"""Router Admin — Endpoints d'administration et migration de données."""

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
