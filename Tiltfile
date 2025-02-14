# Tiltfile
load("ext://dotenv", "dotenv")
dotenv()

# Run using poetry
local_resource("install-deps", "poetry install", deps=["pyproject.toml", "poetry.lock"])

local_resource("format", "poetry run black src/", deps=["src"], auto_init=False)

local_resource("lint", "poetry run ruff check src/", deps=["src"], auto_init=False)

local_resource(
    "db-migrate",
    "poetry run alembic upgrade head",
    deps=["alembic/versions"],
    resource_deps=["install-deps"],
)
