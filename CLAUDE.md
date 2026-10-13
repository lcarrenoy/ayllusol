# CLAUDE.md — AylluSol

Conversation in Spanish; code, commits and identifiers in English. Explain the why.

## Goal
Hackathon MVP (deadline: Tue 2026-10-13 01:59 Lima). Digital "fiado" ledger for bodegas:
voice capture → running account per neighbor → neighbor confirms → daily Merkle root sealed on Solana devnet.

## Stack
FastAPI + SQLAlchemy (SQLite in dev, PostgreSQL later) · React + TS PWA · LangGraph agent ·
Anchor program on Solana devnet · WhatsApp Cloud API (simulated if not configured).

## Rules
1. The ledger is append-only: errors are fixed with adjustment entries, never edits.
2. Money is Decimal / NUMERIC(12,2), never float.
3. Payments apply FIFO to the oldest charge (drives aging).
4. On-chain only hashes and counters. No names, phones or amounts.
5. The AI proposes; a human confirms anything that moves money.
6. Demo uses invented data only. No real customers, RUC or store owner data in the repo.
7. Secrets only in .env (gitignored). Python via `uv`.

## State
Read `docs/PROGRESO.md` at the start of every session; update it before closing.
