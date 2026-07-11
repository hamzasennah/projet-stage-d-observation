# Verification

## Controle fonctionnel

1. Le backend demarre avec `uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload`.
2. `GET /api/health` retourne `{"status": "ok"}`.
3. `POST /api/analyze/documents` accepte une fiche de test et plusieurs CV.
4. Le pipeline cree des embeddings Gemini et indexe les chunks dans ChromaDB.
5. Gemini genere un JSON avec score, resume, points forts, points faibles et detail par critere.
6. Chaque candidat contient des preuves textuelles issues du retrieval ChromaDB.

## Validations effectuees

- `pytest` : tests backend en mode `RAG_TEST_MODE=1`.
- `python -m compileall app` : compilation Python.
- Analyse reelle avec `fiche de poste.pdf` + `CV_Hamza_SENNAH.pdf` : endpoint `POST /api/analyze/documents` retourne `200`.
- Import Kaggle limite : `archive.zip`, 3 CV importes, 25 chunks indexes dans ChromaDB.
- Endpoint base importee : `POST /api/analyze/database` peut classer les CV Kaggle deja importes avec une fiche de poste.

## Controle qualite

- La cle API est chargee depuis `.env`, ignore par Git.
- Les fichiers generes localement (`sqlite3`, `data/chroma`, uploads, `node_modules`, logs) sont ignores par Git.
- L'application normale ne retombe pas silencieusement sur un faux RAG si Gemini est absent.
- Les uploads refusent les formats non supportes.

## Commandes

```powershell
cd backend
pytest
python -m compileall app
```

```powershell
cd frontend
pnpm run build
```
