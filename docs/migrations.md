# Database migrations

Migrations use [Alembic](https://alembic.sqlalchemy.org/en/latest/tutorial.html).
Set `DATABASE_URL` in the environment. Back up persistent data before an upgrade.

New database, before seeding or starting the API:

```powershell
python -m scripts.migrate
python -m scripts.seed seed/gist-cafe.json
```

Existing database created by this project's original schema:

```powershell
python -m scripts.migrate --adopt-existing
```

Adoption compares the schema with the application models before recording the
baseline revision. Differences stop the command for review; existing rows stay.
Use this only for the initial adoption. Afterwards, run `python -m scripts.migrate`
on each release, before starting the API. Startup still creates missing tables
for local convenience; it does not upgrade existing columns.

For a schema change, update the models, then generate and review a migration:

```powershell
python -m alembic revision --autogenerate -m "describe the change"
python -m scripts.migrate
```

Check both fresh installation and upgrade from the previous revision with data.
Review generated operations before committing; renames and data transformations
need explicit migrations. Run migrations once per deployment, with app writes stopped.
