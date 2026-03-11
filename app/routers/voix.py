"""Router Voix du Terrain — Transcription + Résumé IA."""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from typing import Optional
from app.models.schemas import (
    VoixSummaryRequest,
    VoixSummaryResponse,
    VoixFullResponse,
    TranscriptionResponse,
)
from app.services.odoo import get_odoo_client
from app.services.claude_ai import summarize_transcription
from app.services.transcription import transcribe_audio

router = APIRouter(prefix="/api/voix", tags=["Voix du Terrain"])


@router.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe(file: UploadFile = File(...)):
    """Transcrit un fichier audio en texte.

    Accepte WAV, MP3, M4A, OGG. Utilise Deepgram Nova-2 avec
    diarisation des locuteurs et formatage intelligent.
    """
    allowed_types = [
        "audio/wav",
        "audio/wave",
        "audio/x-wav",
        "audio/mpeg",
        "audio/mp3",
        "audio/mp4",
        "audio/m4a",
        "audio/ogg",
        "audio/webm",
    ]

    content_type = file.content_type or "audio/wav"
    if content_type not in allowed_types and not content_type.startswith("audio/"):
        raise HTTPException(
            status_code=400,
            detail=f"Type de fichier non supporté: {content_type}. "
            "Envoyez un fichier audio (WAV, MP3, M4A, OGG).",
        )

    audio_bytes = await file.read()
    if len(audio_bytes) > 25 * 1024 * 1024:  # 25 MB max
        raise HTTPException(status_code=400, detail="Fichier trop volumineux (max 25 MB)")

    try:
        result = await transcribe_audio(audio_bytes, content_type)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Erreur transcription: {str(e)}")

    return TranscriptionResponse(**result)


@router.post("/summarize", response_model=VoixSummaryResponse)
async def summarize(req: VoixSummaryRequest):
    """Résume une transcription avec l'IA.

    Génère un résumé structuré : points clés, actions à suivre,
    opportunités, alertes, et score de sentiment.
    Optionnellement, enregistre le résumé comme note dans Odoo.
    """
    context = req.context

    # Enrichir avec données Odoo si partner_id fourni
    partner_name = req.partner_name
    if req.partner_id:
        try:
            odoo = get_odoo_client()
            partner = await odoo.get_partner(req.partner_id)
            partner_name = partner.get("name", partner_name)
            # Ajouter contexte client
            score = partner.get("x_score_client", "")
            terr = partner.get("x_territoire")
            terr_name = terr[1] if isinstance(terr, (list, tuple)) else ""
            context += (
                f"\nClient score {score}, territoire {terr_name}. "
                f"Notes: {partner.get('x_notes_terrain', 'Aucune')}"
            )
        except Exception:
            pass  # Continue without enrichment

    try:
        summary_text = await summarize_transcription(
            req.transcription, partner_name, context
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Erreur Claude API: {str(e)}")

    # Log to Odoo if partner_id provided
    logged = False
    note_id = None
    if req.partner_id:
        try:
            odoo = get_odoo_client()
            body = (
                f"<h3>🎙️ Résumé Voix du Terrain</h3>"
                f"<p><em>Transcription automatique — {partner_name}</em></p>"
                f"<hr/>{summary_text.replace(chr(10), '<br/>')}"
            )
            note_id = await odoo.log_note(req.partner_id, body)
            logged = True
        except Exception:
            pass  # Don't fail the whole request

    return VoixSummaryResponse(
        summary=summary_text,
        transcription=req.transcription[:500] + ("..." if len(req.transcription) > 500 else ""),
        partner_name=partner_name,
        logged_to_odoo=logged,
        note_id=note_id,
    )


@router.post("/full", response_model=VoixFullResponse)
async def full_pipeline(
    file: UploadFile = File(...),
    partner_id: Optional[int] = Form(None),
    partner_name: str = Form(""),
    context: str = Form(""),
):
    """Pipeline complet : transcription audio → résumé IA → log Odoo.

    Envoie un fichier audio et reçoit la transcription ET le résumé
    structuré en une seule requête. Idéal pour l'app mobile.
    """
    # Step 1: Transcribe
    audio_bytes = await file.read()
    if len(audio_bytes) > 25 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Fichier trop volumineux (max 25 MB)")

    content_type = file.content_type or "audio/wav"
    transcription_result = await transcribe_audio(audio_bytes, content_type)

    # Step 2: Summarize
    summary_req = VoixSummaryRequest(
        transcription=transcription_result["text"],
        partner_name=partner_name,
        partner_id=partner_id,
        context=context,
    )

    # Reuse summarize logic
    summary_resp = await summarize(summary_req)

    return VoixFullResponse(
        transcription=TranscriptionResponse(**transcription_result),
        summary=summary_resp,
    )
