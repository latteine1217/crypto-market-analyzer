# Migrations Consolidated

As of 2026-01-21, all incremental migrations (001-011) have been consolidated into the base schema: `database/schemas/00_v3_optimized.sql`.

This project currently uses a single source of truth for the database schema to improve maintainability and simplify container initialization.

For any future schema changes, please create new migration scripts in this directory (starting from `012_...`).