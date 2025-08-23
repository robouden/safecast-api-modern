# Local Development Setup

This guide shows how to set up the Safecast API Modern for local development without Docker.

## Prerequisites

- Python 3.11+
- PostgreSQL 14+ with PostGIS extension
- Redis (optional, for background tasks)
- Poetry (Python dependency manager)

## Installation

### 1. Install Poetry

```bash
curl -sSL https://install.python-poetry.org | python3 -
```

### 2. Install PostgreSQL with PostGIS

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install postgresql postgresql-contrib postgis postgresql-14-postgis-3
```

**macOS (with Homebrew):**
```bash
brew install postgresql postgis
brew services start postgresql
```

### 3. Setup Dual Database Architecture

The modernized API uses two databases:
- **PostgreSQL** - Main API data (users, devices, measurements, bgeigie_imports)
- **Elasticsearch** - Real-time ingest data (device streams, air quality, radiation)

**PostgreSQL Setup:**
```bash
# Connect to PostgreSQL
sudo -u postgres psql

# Create database and user
CREATE DATABASE safecast_modern;
CREATE USER safecast WITH PASSWORD 'safecast_dev';
GRANT ALL PRIVILEGES ON DATABASE safecast_modern TO safecast;

# Connect to the new database
\c safecast_modern

# Enable PostGIS extension
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;

# Exit psql
\q
```

**Elasticsearch Setup:**
```bash
# Ubuntu/Debian
wget -qO - https://artifacts.elastic.co/GPG-KEY-elasticsearch | sudo apt-key add -
echo "deb https://artifacts.elastic.co/packages/8.x/apt stable main" | sudo tee /etc/apt/sources.list.d/elastic-8.x.list
sudo apt update && sudo apt install elasticsearch

# macOS
brew install elasticsearch

# Start Elasticsearch
sudo systemctl start elasticsearch  # Linux
brew services start elasticsearch   # macOS
```

### 4. Install Python Dependencies

```bash
# Clone and enter the project directory
cd /path/to/safecast-api-modern

# Install dependencies
poetry install

# Activate virtual environment
poetry shell
```

### 5. Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env file with your settings
nano .env
```

Update the `.env` file:
```env
DATABASE_URL=postgresql+asyncpg://safecast:safecast_dev@localhost:5432/safecast_modern
REDIS_URL=redis://localhost:6379
SECRET_KEY=your-secret-key-change-this
```

### 6. Run Database Migrations

```bash
# Initialize Alembic (first time only)
alembic init alembic

# Create initial migration
alembic revision --autogenerate -m "Initial migration"

# Apply migrations
alembic upgrade head
```

### 7. Start the Development Server

```bash
# Start the API server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at:
- Main API: http://localhost:8000
- Interactive docs: http://localhost:8000/docs
- Alternative docs: http://localhost:8000/redoc

## Optional: Redis Setup

For background task processing (file uploads, data processing):

**Ubuntu/Debian:**
```bash
sudo apt install redis-server
sudo systemctl start redis-server
```

**macOS:**
```bash
brew install redis
brew services start redis
```

## Testing

```bash
# Run tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=app
```

## Development Tools

```bash
# Format code
poetry run black .

# Sort imports
poetry run isort .

# Lint code
poetry run flake8

# Type checking
poetry run mypy app
```

## Database Management

### Reset Database
```bash
# Drop and recreate database
sudo -u postgres psql -c "DROP DATABASE safecast_modern;"
sudo -u postgres psql -c "CREATE DATABASE safecast_modern;"
sudo -u postgres psql -d safecast_modern -c "CREATE EXTENSION IF NOT EXISTS postgis;"

# Re-run migrations
alembic upgrade head
```

### Create Sample Data
```bash
# Run the sample data script (when available)
python scripts/create_sample_data.py
```
