# Architecture du projet

## Objectif

Classer plusieurs CV uploades manuellement par rapport a une fiche de poste importee, en produisant un score defendable et des preuves textuelles. La fiche contient les criteres du poste, les exigences, le profil recherche et les competences demandees.

## Flux principal

```mermaid
flowchart TD
    A["Upload fiche de poste PDF"] --> B["Frontend React"]
    C["Upload CV PDF candidats"] --> B
    B --> D["Backend FastAPI"]
    D --> E["Extraction texte fiche"]
    D --> F["Extraction texte CV"]
    E --> G["Reference d'evaluation"]
    F --> H["Decoupage des CV en chunks"]
    H --> I["Embeddings Gemini"]
    I --> J["ChromaDB: index vectoriel de l'analyse"]
    G --> K["Embedding requete fiche"]
    K --> J
    J --> L["Retrieval des passages pertinents"]
    L --> M["Prompt Gemini avec preuves"]
    M --> N["Score + resume + forces/faiblesses"]
    N --> O["Classement final"]
    O --> B
```

## Choix techniques

- FastAPI : API claire, Swagger automatique, support upload multi-fichiers.
- PyMuPDF : extraction du texte des PDF.
- Gemini embeddings : `text-embedding-004`, avec repli `gemini-embedding-001`.
- ChromaDB : base vectorielle des chunks de CV uploades.
- Gemini generation : `gemini-flash-lite-latest`, avec repli `gemini-flash-latest`.
- React + TypeScript : interface stable et typage des reponses.

## Role des donnees

- Fiche de poste : reference d'evaluation, pas une base de donnees.
- CV candidats : documents a analyser et a classer.
- ChromaDB : base vectorielle construite a partir des CV uploades pendant l'analyse.

Il n'y a pas de base SQLite dans l'architecture applicative. Les CV ne sont pas precharges dans une base classique : l'utilisateur les depose, puis le systeme les transforme en vecteurs et les exploite via ChromaDB.

## Important

Le systeme n'utilise pas TF-IDF pour le RAG applicatif. Le retrieval passe par ChromaDB + embeddings Gemini. Le mode de test automatise utilise uniquement des embeddings deterministes pour eviter la consommation API pendant `pytest`.

