# PRISM — frontend

SPA (React + TypeScript + Tailwind v4 + Vite) dla trybu nauki PRISM.
Gada z FastAPI (backend w Pythonie) przez REST.

## Uruchomienie

```bash
npm install
npm run dev          # http://localhost:5173
```

Backend musi działać (domyślnie `http://localhost:8000`):

```bash
# w katalogu głównym repo
docker compose up qdrant -d
uv run uvicorn src.main:app --reload
```

Adres backendu można nadpisać zmienną `VITE_API_URL` (np. w `.env.local`).

## Co robi

Tryb "klikalnej ścieżki nauki" (zero pisania):
1. wybierasz książkę (kolekcję Qdrant),
2. po lewej dostajesz uporządkowaną listę tematów (rozdziałów),
3. klikasz temat → czytasz materiał,
4. "Sprawdź się" → klikalne pytania ABCD generowane przez LLM, auto-oceniane.

## Skrypty

- `npm run dev` — dev server
- `npm run build` — typecheck (tsc) + build produkcyjny
- `npm run typecheck` — sam typecheck
