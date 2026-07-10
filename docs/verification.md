# Verification

## Controle fonctionnel

1. Le backend demarre avec `uvicorn app.main:app --reload`.
2. `GET /api/health` retourne `{"status": "ok"}`.
3. `POST /api/analyze/documents` accepte une fiche de test et plusieurs CV.
4. `GET /api/resumes/seed` retourne les CV provisoires du mode test.
5. `POST /api/analyze/seed` retourne un classement trie par score decroissant.
6. Chaque candidat contient un detail de criteres et des preuves.

## Controle qualite

- Les donnees seed sont marquees comme provisoires.
- Les criteres sont ponderes et verifiables.
- Le scoring est deterministe.
- Les uploads refusent les formats non supportes.
- Les fichiers generes localement (`sqlite3`, uploads, `node_modules`) sont ignores par Git.

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
