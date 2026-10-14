# Progreso

Actualizado: 2026-10-12

## Estado actual
- Web app móvil en `index.html` (GitHub Pages): mostrador con dictado por voz, confirmación del vecino (WhatsApp simulado), pagos FIFO, límites que crecen, dashboard (DSO, aging, semáforo) y sello diario en Solana devnet con el programa Memo + verificación.
- Raíz Merkle del navegador verificada igual a la de Python (`apps/api/ayllusol_api/ledger.py`).
- API FastAPI en memoria con 7 pruebas.

## Persistencia (rama `feat/persistence`, hecha en la laptop el 2026-10-12)
- SQLAlchemy 2 (SQLite en dev, `DATABASE_URL` en `.env`): tablas `customers`, `ledger_entries`, `confirmations`, `seals`.
- Dinero en centavos enteros en SQLite y NUMERIC(12,2) en PostgreSQL (tipo `Money`).
- El libro es inmutable: un listener bloquea UPDATE/DELETE; la confirmación del vecino es una fila aparte.
- `GET /customers`, `GET /customers/{id}/entries`, `POST /seal/{día}` guarda la raíz.
- Seed de demo: `cd apps/api && uv run python -m ayllusol_api.seed`. Pruebas: 12/12.

## Siguiente paso
- Publicar GitHub Pages (Settings → Pages → main /docs) y grabar el video demo.

## Pendientes
- [ ] Programa Anchor `seal_day` (PDA por tienda/día).
- [ ] Persistencia SQLAlchemy.
- [ ] WhatsApp Cloud API real.

## Decisiones recientes
- 2026-10-12 — Sin laptop: la demo es una web estática que firma desde el celular con una billetera devnet propia (localStorage). El sello usa el programa Memo; Anchor queda para después.
