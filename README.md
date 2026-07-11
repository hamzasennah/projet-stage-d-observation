# AI-Powered Resume Ranking System avec vrai RAG

Projet PFE / stage d'observation : application de classement de CV par rapport a une fiche de poste, avec embeddings Gemini, base vectorielle ChromaDB, generation Gemini et dashboard React.

## Ce qui est livre

- Backend FastAPI avec parsing PDF/DOCX/TXT/MD.
- Pipeline RAG reel : extraction, chunks, embeddings Gemini, stockage ChromaDB, retrieval par similarite.
- Analyse LLM Gemini : score, resume, points forts, points faibles, detail par critere et preuves.
- Fiche de test PDF/DOCX/TXT importable : criteres du poste, exigences, profil recherche et competences demandees.
- Base SQLite pour stocker les CV importes et les resultats d'analyse.
- Importeur Kaggle pour `archive.zip` : lecture de `Resume/Resume.csv`, stockage SQLite, indexation ChromaDB.
- Frontend React/TypeScript pour importer une fiche de test, importer des CV et afficher le classement.
- Tests backend avec `pytest` en mode `RAG_TEST_MODE=1` sans appel API externe.

## Modeles Gemini

Configuration actuelle :

- Generation : `gemini-flash-lite-latest`
- Repli generation : `gemini-flash-latest`
- Embeddings : `text-embedding-004`
- Repli embeddings : `gemini-embedding-001`

Note : `gemini-2.5-flash-lite` et `gemini-2.5-flash` peuvent apparaitre dans la liste des modeles, mais cette cle/projet renvoie une erreur `NOT_FOUND` pour ces modeles. Les alias `gemini-flash-lite-latest` et `gemini-flash-latest` ont ete testes avec succes.

## Structure

```text
backend/
  app/
    main.py
    database.py
    services/
      gemini_client.py
      vector_store.py
      ranking.py
      kaggle_importer.py
  scripts/import_kaggle_archive.py
data/
  criteria/spm_data_analyst_packaging.json
  chroma/              # genere localement, ignore par Git
  uploads/             # genere localement, ignore par Git
frontend/
  src/
docs/
```

## Configuration locale

Créer un fichier `.env` a la racine du projet, jamais commite :

```env
LLM_PROVIDER=gemini
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_GENERATION_MODEL=gemini-flash-lite-latest
GEMINI_FALLBACK_MODEL=gemini-flash-latest
GEMINI_EMBEDDING_MODEL=text-embedding-004
GEMINI_EMBEDDING_FALLBACK_MODEL=gemini-embedding-001
CHROMA_PATH=data/chroma
VITE_API_URL=http://127.0.0.1:8001
```

## Flux principal

1. Importer une fiche de test PDF contenant les criteres du poste.
2. Importer un ou plusieurs CV PDF.
3. Cliquer sur `Analyser et classer`.
4. Le backend extrait les textes, cree les embeddings Gemini, indexe les chunks dans ChromaDB, recupere les preuves pertinentes, puis Gemini produit l'analyse finale.
5. Lire le classement final avec score, points forts, points faibles et preuves.

La fiche de test n'est pas la base de donnees : elle sert de reference d'evaluation. Les CV sont les documents analyses et classes.

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

## Importer la base Kaggle

Test limite, recommande pour verifier quota et configuration :

```powershell
cd "C:\Users\pc\Documents\travail demander pour mon stage\backend"
python scripts/import_kaggle_archive.py "C:\Users\pc\Desktop\archive.zip" --limit 20 --category INFORMATION-TECHNOLOGY --category BUSINESS-DEVELOPMENT
```

Import complet :

```powershell
python scripts/import_kaggle_archive.py "C:\Users\pc\Desktop\archive.zip"
```

L'import complet indexe les chunks dans ChromaDB avec Gemini embeddings. Il peut consommer du quota API selon le nombre de CV et de chunks.

Une fois l'import lance, l'endpoint `POST /api/analyze/database` classe les CV de la base sans les reuploader. Parametres multipart utiles :

- `criteria_file` : fiche de poste PDF/DOCX/TXT/MD.
- `limit` : nombre maximum de CV a analyser, 20 par defaut.
- `category` : categorie Kaggle optionnelle, par exemple `INFORMATION-TECHNOLOGY`.
- `top_k` : nombre de preuves RAG recuperees par CV.

## Tests

```powershell
cd "C:\Users\pc\Documents\travail demander pour mon stage\backend"
pytest
```

Les tests activent `RAG_TEST_MODE=1` dans `backend/tests/conftest.py` pour valider ChromaDB sans consommer l'API Gemini.

## Endpoints principaux

- `POST /api/analyze/documents` : analyse une fiche de test importee et des CV importes.
- `POST /api/analyze/database` : analyse une fiche de test importee contre les CV Kaggle deja importes.
- `GET /api/resumes/seed` : liste les CV stockes dans SQLite.
- `POST /api/analyze/seed` : analyse les CV stockes dans SQLite avec la fiche par defaut.
- `GET /api/analyses/{id}` : recupere une analyse sauvegardee.
