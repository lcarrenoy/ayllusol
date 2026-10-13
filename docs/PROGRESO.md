# Progreso

Actualizado: 2026-10-12

## Estado actual
- Web app móvil en `index.html` (GitHub Pages): mostrador con dictado por voz, confirmación del vecino (WhatsApp simulado), pagos FIFO, límites que crecen, dashboard (DSO, aging, semáforo) y sello diario en Solana devnet con el programa Memo + verificación.
- Raíz Merkle del navegador verificada igual a la de Python (`apps/api/ayllusol_api/ledger.py`).
- API FastAPI en memoria con 7 pruebas.

## Siguiente paso
- Publicar GitHub Pages (Settings → Pages → main /docs) y grabar el video demo.

## Pendientes
- [ ] Programa Anchor `seal_day` (PDA por tienda/día).
- [ ] Persistencia SQLAlchemy.
- [ ] WhatsApp Cloud API real.

## Decisiones recientes
- 2026-10-12 — Sin laptop: la demo es una web estática que firma desde el celular con una billetera devnet propia (localStorage). El sello usa el programa Memo; Anchor queda para después.
