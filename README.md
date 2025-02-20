# Feedback Video System

## Setup

1. Clone the repository
2. Copy .env.example to .env and fill in your values
3. Install dependencies:
   ```bash
   poetry install
   ```
4. Run the development server:
   ```bash
   poetry run uvicorn src.main:app --reload
   ```

## Development

- API documentation available at http://localhost:8000/docs
- Admin interface at http://localhost:8000/redoc
