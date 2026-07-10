# AI-Powered Resume Ranking System avec RAG

Projet PFE / stage d'observation : application de classement de CV par rapport a une fiche de poste, avec base provisoire de CV, criteres ponderes, recherche de preuves et dashboard React.

## Ce qui est livre

- Backend FastAPI avec parsing PDF/DOCX/TXT/MD.
- Base SQLite provisoire alimentee par plusieurs versions de CV de test.
- Fiche de test PDF/DOCX/TXT importable : criteres du poste, exigences, profil recherche et competences demandees.
- Fiche de test JSON modifiable en mode avance : competences obligatoires, souhaitees, poids et mots-cles.
- Moteur RAG local : decoupage en chunks, vectorisation TF-IDF, recuperation des passages pertinents.
- Scoring explicable : score final, detail par critere, points forts, points faibles et preuves.
- Frontend React/TypeScript pour importer une fiche de test, importer des CV et afficher le classement.
- Tests backend avec `pytest`.

## Structure

```text
backend/
  app/
    main.py
    database.py
    services/
  tests/
data/
  criteria/data_ai_stage.json
  resumes/seed/
  resumes/seed_manifest.json
frontend/
  src/
docs/
```

## Flux principal

1. Importer une fiche de test PDF contenant les criteres du poste.
2. Importer un ou plusieurs CV PDF.
3. Cliquer sur `Analyser et classer`.
4. Lire le classement final avec score, points forts, points faibles et preuves.

La fiche de test n'est pas la base de donnees : elle sert de reference d'evaluation. Les CV sont les documents analyses et classes.

## Lancer le backend

```powershell
cd "C:\Users\pc\Documents\travail demander pour mon stage\backend"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
uvicorn app.main:app --reload
```

API : [http://127.0.0.1:8000](http://127.0.0.1:8000)  
Swagger : [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

## Lancer le frontend

```powershell
cd "C:\Users\pc\Documents\travail demander pour mon stage\frontend"
pnpm install
pnpm run dev
```

Interface : [http://127.0.0.1:5173](http://127.0.0.1:5173)

Le projet contient un `pnpm-lock.yaml` et un `pnpm-workspace.yaml` pour autoriser le build local d'esbuild de maniere explicite.

## Tests

```powershell
cd "C:\Users\pc\Documents\travail demander pour mon stage\backend"
pytest
```

## Donnees provisoires

Les fichiers dans `data/resumes/seed/` sont des variantes de test inspirees du CV source de Hamza Sennah. Elles servent uniquement a verifier l'algorithme de classement. Pour remplacer la base :

1. Ajouter les nouveaux fichiers `.txt`, `.md`, `.pdf` ou `.docx`.
2. Mettre a jour `data/resumes/seed_manifest.json`.
3. Relancer `POST /api/resumes/reseed` ou redemarrer le backend.

## Endpoints principaux

- `GET /api/criteria/default` : fiche de test par defaut.
- `GET /api/resumes/seed` : CV de la base provisoire.
- `POST /api/analyze/documents` : analyse une fiche de test importee et des CV importes.
- `POST /api/analyze/seed` : analyse la base provisoire.
- `GET /api/analyses/{id}` : recupere une analyse sauvegardee.

## Notes de qualite

Le systeme reste utilisable sans cle LLM : le scoring est local, deterministe et testable. Une integration Gemini/OpenAI peut etre ajoutee ensuite dans `backend/app/services/rag_engine.py` pour enrichir les resumes, sans changer le contrat API.
