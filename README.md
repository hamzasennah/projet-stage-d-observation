# AI-Powered Resume Ranking System avec vrai RAG

Projet PFE / stage d'observation : application de classement de CV par rapport a une fiche de poste, avec embeddings Gemini, base vectorielle ChromaDB, generation Gemini et interface React.

## Ce qui est livre

- Backend FastAPI avec parsing PDF pour la fiche de poste et les CV.
- Pipeline RAG reel : extraction, chunks, embeddings Gemini, stockage vectoriel ChromaDB, retrieval par similarite.
- Analyse LLM Gemini : score, resume, points forts, points faibles, detail par critere et preuves.
- Frontend React/TypeScript pour importer une fiche de poste, importer des CV PDF et afficher le classement.
- Tests backend avec `pytest` en mode `RAG_TEST_MODE=1` sans appel API externe.

Il n'y a plus de base SQLite ni de base Kaggle dans le flux applicatif. Les CV importes manuellement deviennent la base documentaire temporaire de l'analyse : ils sont decoupes, vectorises et indexes dans ChromaDB pour le RAG.

## Modeles Gemini

Configuration actuelle :

- Generation : `gemini-flash-lite-latest`
- Repli generation : `gemini-flash-latest`
- Embeddings : `text-embedding-004`
- Repli embeddings : `gemini-embedding-001`

Note : `gemini-2.5-flash-lite` et `gemini-2.5-flash` peuvent apparaitre dans certaines recommandations, mais cette cle/projet renvoie une erreur `NOT_FOUND` pour ces modeles. Les alias `gemini-flash-lite-latest` et `gemini-flash-latest` ont ete testes avec succes.

## Structure

```text
backend/
  app/
    main.py
    services/
      gemini_client.py
      vector_store.py
      ranking.py
      parser.py
      criteria.py
data/
  criteria/spm_data_analyst_packaging.json
  chroma/              # genere localement, ignore par Git
  uploads/             # genere localement, ignore par Git
frontend/
  src/
docs/
```

## Configuration locale

Creer un fichier `.env` a la racine du projet, jamais commite :

```env
LLM_PROVIDER=gemini
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_GENERATION_MODEL=gemini-flash-lite-latest
GEMINI_FALLBACK_MODEL=gemini-flash-latest
GEMINI_EMBEDDING_MODEL=text-embedding-004
GEMINI_EMBEDDING_FALLBACK_MODEL=gemini-embedding-001
VITE_API_URL=http://127.0.0.1:8001
```

## Flux principal

1. Importer une fiche de poste PDF contenant les criteres du poste.
2. Importer un ou plusieurs CV PDF.
3. Cliquer sur `Analyser et classer`.
4. Le backend extrait les textes, decoupe les CV en chunks, cree les embeddings Gemini et indexe les chunks dans ChromaDB.
5. Le moteur RAG recupere les passages les plus pertinents de chaque CV par rapport a la fiche de poste.
6. Gemini produit l'analyse finale : score, resume, points forts, points faibles, detail par critere et preuves.

La fiche de poste n'est pas une base de donnees. Elle sert de reference d'evaluation. Les CV uploades sont les documents analyses et forment l'index vectoriel ChromaDB de l'analyse courante.

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

## Generer des CV PDF de test

Le script suivant cree 20 CV PDF anonymises a partir de l'archive Kaggle locale. Les fichiers sont generes dans `output/pdf/test_cvs/`, ignore par Git.

```powershell
cd "C:\Users\pc\Documents\travail demander pour mon stage"
python tools/generate_test_cv_pdfs.py "C:\Users\pc\Desktop\archive.zip"
```

Ces PDF sont destines a etre uploades manuellement dans l'interface, avec la fiche de poste PDF.

Avec le quota gratuit Gemini, il est conseille de tester par lots de 5 a 10 CV. Le backend applique des retries sur les erreurs `429` et garde un cache local des embeddings dans `data/cache/`, ignore par Git, pour eviter de recalculer les memes vecteurs aux essais suivants.

## Tests

```powershell
cd "C:\Users\pc\Documents\travail demander pour mon stage\backend"
pytest
python -m compileall app
```

```powershell
cd "C:\Users\pc\Documents\travail demander pour mon stage\frontend"
pnpm run build
```

Les tests activent `RAG_TEST_MODE=1` dans `backend/tests/conftest.py` pour valider ChromaDB sans consommer l'API Gemini.

## Endpoint principal

- `POST /api/analyze/documents` : analyse une fiche de poste importee et un ou plusieurs CV PDF importes.
