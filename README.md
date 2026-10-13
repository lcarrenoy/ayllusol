# AylluSol

**A digital "fiado" (store-credit) ledger for neighborhood stores, with daily proofs sealed on Solana.**

Live demo (mobile first): **https://lcarrenoy.github.io/ayllusol/** · Demo video: **https://lcarrenoy.github.io/ayllusol/demo.html**

Across Peru and Latin America, millions of bodegas sell on credit to neighbors they know, tracked in
paper notebooks. Records get lost, disputes are common, and owners don't know how much they are owed
or how long it takes to collect. AylluSol turns that notebook into a shared, tamper-evident ledger.

## What the demo shows

| Tab | What happens |
| --- | --- |
| **Mostrador** (counter) | The owner taps products or dictates ("dos arroz y un aceite para Rosa"). The entry is *proposed*, checked against the neighbor's credit limit, and sent to the neighbor for confirmation (WhatsApp simulated). Payments (Yape, Plin, cash, transfer) are applied FIFO to the oldest debt. |
| **Vecinos** | Each neighbor's balance, payment day and credit limit. Limits grow with on-time payments (+20% each, capped at 2x). |
| **Dashboard** | Receivables, DSO (30 days), aging buckets (0-7, 8-15, 16-30, 31-60, 60+) and a traffic light per neighbor. |
| **Sello** (seal) | The confirmed entries of the day are hashed into a SHA-256 Merkle root and written to **Solana devnet** with the Memo program. "Verificar" reads the transaction back from the chain and recomputes the root: if anyone edited the notebook after sealing, it no longer matches. |

## Why Solana

One transaction per store per day costs a fraction of a cent and confirms in seconds, so every
bodega can anchor its books daily. **Only the hash goes on-chain**: no names, phones or amounts.
The store and the neighbor keep the data; the chain keeps the proof.

Memo format: `ayllusol:v1|store:<id>|day:<YYYY-MM-DD>|n:<entries>|root:<sha256 hex>`

## Design rules

1. Append-only ledger: errors are fixed with adjustment entries, never edits.
2. Money in integer cents / `Decimal`, never float.
3. Payments apply FIFO to the oldest charge (this drives aging and DSO).
4. On-chain: only hashes and counters.
5. The AI proposes; a human confirms anything that moves money.
6. Demo data is invented.

## Repository

```
index.html              Mobile web app (GitHub Pages) — counter, dashboard, Solana devnet seal
apps/api/               Python ledger core + FastAPI (balances, FIFO aging, DSO, Merkle root) with tests
programs/ayllu_ledger/  Planned Anchor program (seal_day PDA per store/day) — next step
docs/PROGRESO.md        Progress log
```

The web app and the Python core use the **same hashing and Merkle algorithm** (sorted leaves,
odd node paired with itself), so a root computed in the browser can be re-verified by the backend.

### Run the API tests

```bash
cd apps/api
uv sync
uv run pytest
```

## Roadmap

- Anchor program with a PDA per store/day (replaces the Memo seal, enables on-chain queries).
- Real WhatsApp Cloud API confirmations and receipt-screenshot reading for Yape/Plin.
- Reconciliation from photos of paper notebooks.
- Netting debts between neighborhood businesses.
- Postgres with row-level security per store.

Built for the Colosseum Crypto World's Fair hackathon (Solana track).
