# Resume Ranking RAG

Application PFE de classement de CV par rapport a une fiche de poste. Le flux reel du code actuel est simple : l'utilisateur importe une fiche de poste et des CV, le backend extrait le texte, construit un index vectoriel ChromaDB avec des embeddings Gemini, recupere les passages pertinents, puis Gemini produit le classement.

## Fonctionnalites actuelles

- Interface React pour importer une fiche de poste PDF et un ou plusieurs CV PDF.
- API FastAPI avec endpoint principal `POST /api/analyze/documents`.
- Extraction de texte via PyMuPDF pour les PDF. Le backend sait aussi extraire DOCX/TXT/MD, mais l'interface actuelle limite la selection aux PDF.
- Decoupage des CV en chunks, embeddings Gemini et stockage/recherche dans ChromaDB.
- Scoring LLM Gemini avec resume, points forts, points faibles, detail par critere et preuves RAG.
- Cache local des embeddings dans `data/cache/` pour eviter de recalculer les memes vecteurs.
- Tests backend en mode `RAG_TEST_MODE=1`, sans appel API Gemini.
- Script optionnel de generation de CV PDF anonymises pour les tests.

## Ce qui n'existe pas dans l'application actuelle

- Pas de base SQLite applicative.
- Pas de base permanente de CV.
- Pas d'import Kaggle dans le backend de production.
- Pas d'historique d'analyses sauvegarde.
- Pas d'endpoint `/api/analyze/database`, `/api/analyze/seed` ou `/api/resumes/seed`.
- Pas de limite applicative fixe sur le nombre de CV uploades. Les limites pratiques viennent du temps de traitement, de la taille des fichiers et du quota Gemini.

## Modeles Gemini

Valeurs par defaut dans `backend/app/config.py` :

- Generation : `gemini-flash-lite-latest`
- Repli generation : `gemini-flash-latest`
- Embeddings : `text-embedding-004`
- Repli embeddings : `gemini-embedding-001`

Si Gemini retourne `429`, l'application renvoie un message de quota. Le code applique quelques retries et garde un cache local, mais il ne peut pas contourner un quota quotidien epuise.

## Structure utile

```text
backend/
  app/
    main.py              # endpoints FastAPI
    config.py            # configuration et variables d'environnement
    schemas.py           # schemas de requete/reponse
    models.py            # modeles internes
    services/
      parser.py          # extraction PDF/DOCX/TXT/MD
      criteria.py        # construction de la fiche de criteres
      chunker.py         # decoupage des textes
      gemini_client.py   # embeddings + generation Gemini + cache
      vector_store.py    # ChromaDB
      ranking.py         # orchestration RAG + scoring
      rag_engine.py      # conversion des resultats API
  tests/
frontend/
  src/
    App.tsx
    api.ts
    components/
      DocumentAnalyzer.tsx
      RankingTable.tsx
data/
  criteria/spm_data_analyst_packaging.json
  uploads/               # genere localement, ignore par Git
  chroma/                # genere localement, ignore par Git
  cache/                 # genere localement, ignore par Git
tools/
  generate_test_cv_pdfs.py
```

## Configuration locale

Creer un fichier `.env` a la racine du projet. Il est ignore par Git.

```env
LLM_PROVIDER=gemini
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_GENERATION_MODEL=gemini-flash-lite-latest
GEMINI_FALLBACK_MODEL=gemini-flash-latest
GEMINI_EMBEDDING_MODEL=text-embedding-004
GEMINI_EMBEDDING_FALLBACK_MODEL=gemini-embedding-001
VITE_API_URL=http://127.0.0.1:8001
```

## Lancer le backend

```powershell
cd "C:\Users\pc\Documents\travail demander pour mon stage\backend"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload
```

API : [http://127.0.0.1:8001](http://127.0.0.1:8001)  
Swagger : [http://127.0.0.1:8001/docs](http://127.0.0.1:8001/docs)

## Lancer le frontend

```powershell
cd "C:\Users\pc\Documents\travail demander pour mon stage\frontend"
pnpm install
$env:VITE_API_URL="http://127.0.0.1:8001"
pnpm run dev
```

Interface : [http://127.0.0.1:5173](http://127.0.0.1:5173)

## Flux utilisateur

1. Importer une fiche de poste PDF.
2. Importer un ou plusieurs CV PDF.
3. Cliquer sur `Analyser et classer`.
4. Lire le classement : score, resume, points forts, points faibles, detail des criteres et preuves.

La fiche de poste sert de reference d'evaluation. Les CV uploades deviennent la base documentaire temporaire de l'analyse : ils sont decoupes, vectorises et indexes dans ChromaDB pour le run courant.

## Endpoints actuels

- `GET /` : statut simple de l'API.
- `GET /api/health` : controle de sante.
- `GET /api/criteria/default` : fiche de criteres JSON par defaut.
- `POST /api/analyze/documents` : analyse une fiche de poste et des CV uploades.

## Generer des CV PDF de test

Le script `tools/generate_test_cv_pdfs.py` est un outil local de test. Il lit `archive.zip`, anonymise des lignes du dataset et genere 20 PDF dans `output/pdf/test_cvs/`. Ces PDF ne sont pas versionnes.

Installer la dependance du script si elle n'est pas deja presente :

```powershell
python -m pip install reportlab
```

Generer les PDF :

```powershell
cd "C:\Users\pc\Documents\travail demander pour mon stage"
python tools/generate_test_cv_pdfs.py "C:\Users\pc\Desktop\archive.zip"
```

Ces fichiers servent uniquement de CV de test a uploader manuellement dans l'interface.

## Tests

Backend :

```powershell
cd "C:\Users\pc\Documents\travail demander pour mon stage\backend"
pytest
python -m compileall app
```

Frontend :

```powershell
cd "C:\Users\pc\Documents\travail demander pour mon stage\frontend"
pnpm run build
```

Les tests activent `RAG_TEST_MODE=1` dans `backend/tests/conftest.py`. Dans ce mode, les embeddings sont deterministes et aucun appel Gemini n'est consomme.

