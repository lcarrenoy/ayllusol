# Progreso

Actualizado: 2026-10-12

## Estado actual
- Web app móvil en `index.html` (GitHub Pages): mostrador con dictado por voz, confirmación del vecino (WhatsApp simulado), pagos FIFO, límites que crecen, dashboard (DSO, aging, semáforo) y sello diario en Solana devnet con el programa Memo + verificación.
- Raíz Merkle del navegador verificada igual a la de Python (`apps/api/ayllusol_api/ledger.py`).
- API FastAPI en memoria con 7 pruebas.

## En rama `feat/catalog-voice` (no publicada hasta que termine la evaluación)
- Pestaña Productos: agregar/editar/quitar con costo, precio y margen; registro por voz ("leche gloria tarro, costo tres cincuenta, precio cuatro treinta").
- Importar catálogo desde Excel/CSV en el teléfono (los datos no se suben; nunca al repo).
- Mostrador con buscador y productos más usados; voz usa el catálogo completo; pagos por voz ("Rosa pagó veinte soles con Yape").
- Dashboard: margen bruto estimado del fiado (costo guardado en cada venta).

## Siguiente paso
- Publicar GitHub Pages (Settings → Pages → main /docs) y grabar el video demo.

## Pendientes
- [ ] Programa Anchor `seal_day` (PDA por tienda/día).
- [ ] Persistencia SQLAlchemy.
- [ ] WhatsApp Cloud API real.

## Decisiones recientes
- 2026-10-12 — Sin laptop: la demo es una web estática que firma desde el celular con una billetera devnet propia (localStorage). El sello usa el programa Memo; Anchor queda para después.
