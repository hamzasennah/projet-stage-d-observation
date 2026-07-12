# Verification

## Controle fonctionnel

1. Le backend demarre avec `uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload`.
2. `GET /api/health` retourne `{"status": "ok"}`.
3. `POST /api/analyze/documents` accepte une fiche de poste PDF et plusieurs CV PDF.
4. Le pipeline cree des embeddings Gemini et indexe les chunks des CV dans ChromaDB.
5. Gemini genere un JSON avec score, resume, points forts, points faibles et detail par critere.
6. Chaque candidat contient des preuves textuelles issues du retrieval ChromaDB.

## Validations a executer

- `pytest` : tests backend en mode `RAG_TEST_MODE=1`.
- `python -m compileall app` : compilation Python.
- `pnpm run build` : build frontend.
- Test backend avec 12 CV dans une seule requete : aucune limite applicative fixe sur le nombre de CV.
- Analyse reelle avec `fiche de poste.pdf` + plusieurs CV PDF : endpoint `POST /api/analyze/documents` doit retourner `200`.

## Controle qualite

- La cle API est chargee depuis `.env`, ignore par Git.
- Les fichiers generes localement (`data/chroma`, uploads, `node_modules`, logs) sont ignores par Git.
- L'application normale ne retombe pas silencieusement sur un faux RAG si Gemini est absent.
- Les uploads refusent les formats non supportes.
- Aucune base SQLite, aucun import Kaggle et aucun jeu de CV seed ne sont requis dans le flux principal.

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
