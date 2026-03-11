"""Service de transcription audio — Deepgram + fallback Whisper."""

import io
from app.config import get_settings


async def transcribe_audio(audio_bytes: bytes, mimetype: str = "audio/wav") -> dict:
    """Transcribe audio using Deepgram.

    Returns dict with 'text' (full transcript) and 'segments' (word-level).
    """
    settings = get_settings()

    if not settings.deepgram_api_key:
        return {
            "text": "[Transcription simulée — clé Deepgram non configurée] "
            "Bonjour, c'est le représentant de Granites MC. On a parlé des "
            "comptoirs en Silestone pour le projet de condos à Magog. Le client "
            "veut 24 unités, livraison en juin. Il hésite entre Silestone et "
            "Caesarstone. Il a mentionné que Granit Design lui a fait une offre. "
            "Il faudrait revenir avec un prix compétitif et des échantillons de "
            "la nouvelle collection.",
            "segments": [],
            "is_simulated": True,
        }

    # Deepgram real transcription
    from deepgram import DeepgramClient, PrerecordedOptions

    dg = DeepgramClient(settings.deepgram_api_key)

    source = {"buffer": audio_bytes, "mimetype": mimetype}
    options = PrerecordedOptions(
        model="nova-2",
        language="fr",
        smart_format=True,
        punctuate=True,
        diarize=True,  # Speaker diarization
        utterances=True,
    )

    response = await dg.listen.asyncrest.v("1").transcribe_file(source, options)
    result = response.to_dict()

    transcript = result["results"]["channels"][0]["alternatives"][0]["transcript"]
    words = result["results"]["channels"][0]["alternatives"][0].get("words", [])

    segments = []
    for w in words:
        segments.append(
            {
                "word": w["word"],
                "start": w["start"],
                "end": w["end"],
                "speaker": w.get("speaker", 0),
                "confidence": w.get("confidence", 0),
            }
        )

    return {
        "text": transcript,
        "segments": segments,
        "is_simulated": False,
    }
