#!/bin/bash

# create_project.sh
PROJECT_NAME="video_generator"

# Create base directory
mkdir -p $PROJECT_NAME
cd $PROJECT_NAME

# Create directory structure
mkdir -p src/{models,services,utils}
mkdir -p alembic/versions

# Create __init__.py files
touch src/__init__.py
touch src/models/__init__.py
touch src/services/__init__.py
touch src/utils/__init__.py

# Create .env
cat > .env << EOL
SYNTHESIA_API_KEY=your_key_here
DB_URL=sqlite:///feedback_videos.db
ENVIRONMENT=development
LOG_LEVEL=INFO
EOL

# Create requirements.txt
cat > requirements.txt << EOL
pydantic
sqlalchemy
aiohttp
alembic
python-dotenv
EOL

# Create requirements-dev.txt
cat > requirements-dev.txt << EOL
-r requirements.txt
black
ruff
EOL

# Create Tiltfile
cat > Tiltfile << EOL
# Load env vars
load('ext://dotenv', 'dotenv')
dotenv()

# Install production dependencies
local_resource(
    'install-deps',
    'pip install -r requirements.txt',
    deps=['requirements.txt']
)

# Install development dependencies
local_resource(
    'install-dev-deps',
    'pip install -r requirements-dev.txt',
    deps=['requirements-dev.txt'],
    resource_deps=['install-deps']
)

# Run database migrations
local_resource(
    'setup-db',
    'python -m alembic upgrade head',
    deps=['alembic/versions'],
    resource_deps=['install-deps']
)

# Format code with black
local_resource(
    'format',
    'black src/',
    deps=['src'],
    auto_init=False
)

# Lint with ruff
local_resource(
    'lint',
    'ruff check src/',
    deps=['src'],
    auto_init=False
)

# Run the script
local_resource(
    'video-generator',
    'python src/main.py',
    deps=['src'],
    resource_deps=['setup-db'],
    auto_init=False
)
EOL

# Create pyproject.toml
cat > pyproject.toml << EOL
[tool.black]
line-length = 88
target-version = ['py39']
include = '\.pyi?$'

[tool.ruff]
line-length = 88
select = ["E", "F", "B"]
ignore = ["E501"]
EOL

# Create settings.py
cat > src/settings.py << EOL
from pydantic import BaseSettings

class Settings(BaseSettings):
    SYNTHESIA_API_KEY: str
    DB_URL: str = "sqlite:///feedback_videos.db"
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"

    class Config:
        env_file = ".env"
EOL

# Create main.py
cat > src/main.py << EOL
import asyncio
import logging
from settings import Settings

logging.basicConfig(level=Settings().LOG_LEVEL)
logger = logging.getLogger(__name__)

async def main():
    logger.info("Starting video generator")

if __name__ == "__main__":
    asyncio.run(main())
EOL

# Make script executable
chmod +x src/main.py

echo "Project structure created successfully!"
echo "Next steps:"
echo "1. cd $PROJECT_NAME"
echo "2. Update .env with your Synthesia API key"
echo "3. tilt up to start development environment"
