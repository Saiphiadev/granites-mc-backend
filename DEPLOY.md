# Déploiement — Backend IA Granites MC

## 1. Push vers GitHub

Le repo a été créé : https://github.com/Saiphiadev/granites-mc-backend

```bash
cd backend
git init
git add .
git commit -m "feat: backend IA avec Coach de Vente et Voix du Terrain"
git branch -M main
git remote add origin https://github.com/Saiphiadev/granites-mc-backend.git
git push -u origin main
```

**Note :** Ne pas commiter le fichier `.env` (contient les secrets).

## 2. Déployer sur Railway

1. Aller sur https://railway.app
2. New Project → Deploy from GitHub repo
3. Sélectionner `Saiphiadev/granites-mc-backend`
4. Ajouter les variables d'environnement dans Railway :
   - `ODOO_URL` = https://granites-mc.odoo.com
   - `ODOO_DB` = granites-mc
   - `ODOO_USER` = (ton email)
   - `ODOO_PASSWORD` = (ton mot de passe Odoo)
   - `ANTHROPIC_API_KEY` = (ta clé Claude API)
   - `DEEPGRAM_API_KEY` = (optionnel, pour transcription réelle)
   - `PORT` = 8000
5. Railway va auto-détecter le Dockerfile et déployer

## 3. Tester les endpoints

Une fois déployé, l'API Swagger est disponible à :
`https://[ton-domaine-railway].up.railway.app/docs`

### Endpoints disponibles :

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/health` | État du backend |
| GET | `/api/coach/territories` | Liste des territoires |
| GET | `/api/coach/partners` | Liste des clients (filtrable) |
| POST | `/api/coach/briefing` | Générer un briefing pré-visite |
| POST | `/api/voix/transcribe` | Transcrire un audio |
| POST | `/api/voix/summarize` | Résumer une transcription |
| POST | `/api/voix/full` | Pipeline complet audio→résumé |

### Exemple — Briefing pré-visite :
```bash
curl -X POST https://[domaine]/api/coach/briefing \
  -H "Content-Type: application/json" \
  -d '{"partner_id": 100}'
```

### Exemple — Résumé de transcription :
```bash
curl -X POST https://[domaine]/api/voix/summarize \
  -H "Content-Type: application/json" \
  -d '{
    "transcription": "Le client veut 24 comptoirs Silestone...",
    "partner_name": "Cuisifab",
    "partner_id": 100
  }'
```
