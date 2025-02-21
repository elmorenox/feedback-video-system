#!/bin/bash

# Project name
PROJECT_NAME="feedback-video-system"

# Create project directory
mkdir $PROJECT_NAME
cd $PROJECT_NAME

# Create main directory structure
mkdir -p src/{api/{dependencies,middleware,routes,exceptions},models,services,schema}
mkdir -p tests

# Create API structure with empty files
touch src/api/__init__.py
touch src/api/dependencies/{__init__,auth,db}.py
touch src/api/middleware/{__init__,logging}.py
touch src/api/routes/{__init__,videos,webhooks}.py
touch src/api/exceptions/{__init__,handlers}.py

# Create other needed directories with init files
touch src/__init__.py
touch src/models/__init__.py
touch src/services/__init__.py
touch src/schema/__init__.py

# Create basic main.py
cat > src/main.py << EOL
from fastapi import FastAPI

app = FastAPI(title="Feedback Video System")

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
EOL

# Create pyproject.toml
cat > pyproject.toml << EOL
[tool.poetry]
name = "feedback-video-system"
version = "0.1.0"
description = "Automated feedback video generation system"
authors = ["Your Name <your.email@example.com>"]

[tool.poetry.dependencies]
python = "^3.9"
fastapi = "^0.109.2"
uvicorn = "^0.27.1"
sqlalchemy = "^2.0.25"
httpx = "^0.26.0"
python-dotenv = "^1.0.0"
sshtunnel = "^0.4.0"
langchain = "^0.1.4"
openai = "^1.10.0"
python-multipart = "^0.0.6"
descript-api = "^0.0.5"
pymysql = "^1.1.0"
alembic = "^1.13.1"

[tool.poetry.group.dev.dependencies]
pytest = "^8.0.0"
pytest-asyncio = "^0.23.4"
black = "^24.1.1"
isort = "^5.13.2"
mypy = "^1.8.0"

[build-system]
requires = ["poetry-core>=1.0.0"]
build-backend = "poetry.core.masonry.api"
EOL

# Create env file template
cat > .env.example << EOL
# FastAPI
SECRET_KEY=your-secret-key-here
API_VERSION=v1
DEBUG=True

# Databases
DB_URL=sqlite:///./feedback.db
MYSQL_URL=mysql+pymysql://user:pass@host:3306/dbname

# SSH Tunnel
SSH_HOST=your-ssh-host
SSH_PORT=22
SSH_USERNAME=your-ssh-username
SSH_KEY_PATH=/path/to/your/ssh/key

# OpenAI
OPENAI_API_KEY=your-openai-key-here

# HeyGen
HEYGEN_API_KEY=your-heygen-key-here

# Descript
DESCRIPT_API_KEY=your-descript-key-here
EOL

# Create basic settings.py
# Create basic settings.py
cat > src/settings.py << EOL
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # FastAPI
    SECRET_KEY: str
    API_VERSION: str
    DEBUG: bool = False

    # Databases
    DB_URL: str
    MYSQL_URL: str

    # SSH Tunnel
    SSH_HOST: str
    SSH_PORT: int = 22
    SSH_USERNAME: str
    SSH_KEY_PATH: str

    # OpenAI
    OPENAI_API_KEY: str

    # HeyGen
    HEYGEN_API_KEY: str
    
    # Descript
    DESCRIPT_API_KEY: str

    class Config:
        env_file = ".env"

settings = Settings()
EOL

# Create minimal database.py
cat > src/database.py << EOL
"""
TODO: Add your dual-database setup (SQLite + MySQL via SSH Tunnel)
"""

from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()
EOL

# Initialize git repository
git init
cat > .gitignore << EOL
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual Environment
.env
.venv
venv/
ENV/

# IDE
.idea/
.vscode/
*.swp
*.swo

# Project specific
feedback.db
EOL

# Create README
cat > README.md << EOL
# Feedback Video System

## Setup

1. Clone the repository
2. Copy .env.example to .env and fill in your values
3. Install dependencies:
   \`\`\`bash
   poetry install
   \`\`\`
4. Run the development server:
   \`\`\`bash
   poetry run uvicorn src.main:app --reload
   \`\`\`

## Development

- API documentation available at http://localhost:8000/docs
- Admin interface at http://localhost:8000/redoc
EOL

# Initialize poetry and install dependencies
poetry install

# Create initial git commit
git add .
git commit -m "Initial project setup"

echo "Project setup complete! Next steps:"
echo "1. Copy .env.example to .env and fill in your values"
echo "2. Add your implementation to the empty files in the api directory"
echo "3. Run 'poetry install' to install dependencies"
echo "4. Run 'poetry run uvicorn src.main:app --reload' to start the development server"