"""Service Claude API pour génération IA — Granites MC."""

import anthropic
from app.config import get_settings


def get_claude_client() -> anthropic.AsyncAnthropic:
    """Return an async Anthropic client."""
    settings = get_settings()
    return anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)


SYSTEM_PROMPT_COACH = """Tu es le Coach de Vente IA de Les Granites MC Inc., un fabricant/distributeur
de comptoirs de quartz et granite basé à Sherbrooke (Québec).

Tu aides les représentants commerciaux à préparer leurs visites clients en générant des briefings
stratégiques personnalisés. Tu connais très bien :
- L'industrie des comptoirs de cuisine (quartz, granite, Dekton, Laminam)
- Les marques distribuées : Caesarstone, Silestone, Vicostone, Technistone, Hanstone, Dekton, Cambria, Laminam, Corian Quartz
- La clientèle B2B : ébénistes, cuisinistes, designers d'intérieur, constructeurs
- Les territoires au Québec (T01 Outaouais à T09 Québec/Chaudière)
- Les compétiteurs : Granit Design, Castelo, Ciot, Noble, Summum, Extreme, Rouleau, Comptoir Prestige

Tu réponds TOUJOURS en français québécois professionnel. Tu es concis, actionnable et stratégique.
Chaque briefing doit inclure des suggestions concrètes pour maximiser les ventes."""


SYSTEM_PROMPT_VOIX = """Tu es l'assistant Voix du Terrain de Les Granites MC Inc.

Tu reçois des transcriptions de conversations entre représentants commerciaux et clients
(ébénistes, cuisinistes, designers). Tu dois :

1. **Résumé structuré** — Points clés de la conversation (3-5 bullets max)
2. **Actions à suivre** — Tâches concrètes avec priorité (haute/moyenne/basse)
3. **Opportunités détectées** — Ventes croisées, nouveaux besoins, projets à venir
4. **Alertes** — Insatisfactions, risques de perte, mentions de compétiteurs
5. **Score sentiment** — 1 (très négatif) à 5 (très positif) avec justification

Tu réponds TOUJOURS en français. Tu es précis et orienté action."""


async def generate_briefing(partner_data: dict, context: str = "") -> str:
    """Generate a pre-visit sales briefing for a partner."""
    client = get_claude_client()

    user_prompt = _build_briefing_prompt(partner_data, context)

    message = await client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1500,
        system=SYSTEM_PROMPT_COACH,
        messages=[{"role": "user", "content": user_prompt}],
    )

    return message.content[0].text


async def summarize_transcription(
    transcription: str, partner_name: str = "", context: str = ""
) -> str:
    """Summarize a voice transcription with structured output."""
    client = get_claude_client()

    user_prompt = f"""Voici la transcription d'une conversation terrain :

**Client :** {partner_name or 'Non spécifié'}
{f'**Contexte :** {context}' if context else ''}

---
TRANSCRIPTION :
{transcription}
---

Génère le résumé structuré complet (résumé, actions, opportunités, alertes, score sentiment)."""

    message = await client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1500,
        system=SYSTEM_PROMPT_VOIX,
        messages=[{"role": "user", "content": user_prompt}],
    )

    return message.content[0].text


def _build_briefing_prompt(partner: dict, context: str) -> str:
    """Build the briefing prompt from partner data."""
    territoire = partner.get("x_territoire")
    terr_name = territoire[1] if isinstance(territoire, (list, tuple)) else str(territoire or "Non assigné")

    score = partner.get("x_score_client") or "Non scoré"
    notes = partner.get("x_notes_terrain") or "Aucune note"
    competiteurs = partner.get("x_competiteurs") or "Non documenté"
    marques = partner.get("x_marques_interet") or "Non documenté"
    derniere_visite = partner.get("x_date_derniere_visite") or "Jamais"
    nb_visites = partner.get("x_nb_visites") or 0
    echantillons = partner.get("x_echantillons_notes") or "Aucun"
    type_client = partner.get("x_type_client") or "Non classifié"

    prompt = f"""Prépare un briefing pré-visite pour le client suivant :

**NOM :** {partner.get('name', 'Inconnu')}
**TERRITOIRE :** {terr_name}
**SCORE CLIENT :** {score}
**TYPE :** {type_client}
**ADRESSE :** {partner.get('street', '')} {partner.get('city', '')} {partner.get('zip', '')}
**TÉLÉPHONE :** {partner.get('phone', 'N/A')}
**COURRIEL :** {partner.get('email', 'N/A')}

**NOTES TERRAIN :** {notes}
**COMPÉTITEURS :** {competiteurs}
**MARQUES D'INTÉRÊT :** {marques}
**DERNIÈRE VISITE :** {derniere_visite}
**NB VISITES TOTAL :** {nb_visites}
**ÉCHANTILLONS :** {echantillons}

{f'**CONTEXTE ADDITIONNEL :** {context}' if context else ''}

Génère un briefing structuré avec :
1. **Résumé client** (2-3 lignes)
2. **Objectifs de la visite** (3 objectifs prioritaires)
3. **Points de discussion suggérés** (adaptés au profil)
4. **Produits à proposer** (basé sur marques d'intérêt et compétiteurs)
5. **Alertes / Points d'attention** (risques, opportunités)
6. **Question d'ouverture suggérée** (pour démarrer la conversation)"""

    return prompt
