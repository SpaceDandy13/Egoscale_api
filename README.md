# egoscale_api

This repository now focuses purely on asynchronous PostgreSQL data operations. It provides:

- A production-ready `DatabaseManager` built on top of `asyncpg` with retry logic and
  dozens of helpers for points, warnings, wallet bindings, OAuth state, and auditing tables.
- Connection/bootstrap helpers in `database/config.py` that read a `DATABASE_URL` and expose a pooled connection.
- SQL schema files (`database/schema_postgres.sql`) that can be executed as-is to provision every table used by the
  helper methods.
- A lightweight performance harness `performance_test_simple.py` you can run locally to verify latency and throughput
  for common operations (daily check-ins, leaderboard updates, etc.).

All Discord-, OAuth-, and bot-related code has been removed so that this project can be embedded into any backend that
needs mature data-access utilities without carrying unrelated business logic.

## Getting Started

1. **Clone the project**
   ```bash
   git clone <your-fork-url>
   cd egoscale_api
   ```
2. **Provide database credentials**
   - Copy `.env.example` to `.env` (or set environment variables another way).
   - Update `DATABASE_URL` to a valid PostgreSQL connection string, e.g.
     `postgresql://user:password@localhost:5432/mydb`.
3. **Install dependencies**
   ```bash
   python -m pip install -r requirements.txt
   ```
4. **Run the performance probe (optional)**
   ```bash
   python performance_test_simple.py
   ```
   The script opens a connection pool, exercises several high-traffic data paths, and prints timing metrics.

## Project Layout

```
database/
  __init__.py            # DatabaseManager implementation (warns, points, wallet binding, OAuth, logs...)
  config.py              # Connection helpers that build asyncpg pools from DATABASE_URL
  schema_postgres.sql    # Schema used by DatabaseManager helpers
.env.example             # Minimal configuration sample (DATABASE_URL only)
performance_test_simple.py  # Async probe for latency & concurrency validation
requirements.txt         # Runtime dependencies (asyncpg only)
```

## Extending the Toolkit

- **Custom queries** – instantiate `DatabaseManager` with the shared asyncpg pool and add new helper methods next to
  existing ones for consistency.
- **Schema migrations** – append statements to `database/schema_postgres.sql` so new environments can be provisioned by
  simply executing the file once.
- **Load testing** – duplicate the patterns in `performance_test_simple.py` to benchmark your own read/write flows
  before wiring the manager into higher-level services.

## License

This project remains under the Apache License 2.0. See [LICENSE.md](LICENSE.md) for details.
