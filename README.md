# Safecast API Modern

A modernized version of the Safecast API built with FastAPI, maintaining compatibility with the original Rails API while providing improved performance, maintainability, and developer experience.

## Key Improvements

- **FastAPI**: Modern Python framework with automatic OpenAPI documentation
- **Async/Await**: Non-blocking I/O for better performance
- **Pydantic**: Type validation and serialization
- **SQLAlchemy 2.0**: Modern ORM with async support
- **PostGIS**: Maintained spatial data capabilities
- **Docker**: Containerized deployment
- **Poetry**: Modern dependency management

## Architecture

```
├── app/
│   ├── api/           # API routes and endpoints
│   ├── core/          # Configuration and security
│   ├── models/        # Database models
│   ├── schemas/       # Pydantic schemas
│   ├── services/      # Business logic
│   └── utils/         # Utilities and helpers
├── alembic/           # Database migrations
├── tests/             # Test suite
└── docker/            # Docker configuration
```

## Quick Start

```bash
# Install dependencies
poetry install

# Start database
docker-compose up -d postgres

# Run migrations
alembic upgrade head

# Start development server
poetry run uvicorn app.main:app --reload
```

## API Compatibility

This implementation maintains full backward compatibility with the original Safecast API:

- Same endpoint URLs and parameters
- Identical response formats
- Compatible authentication
- Preserved spatial query capabilities

## Documentation

- API docs: http://localhost:8000/docs
- Alternative docs: http://localhost:8000/redoc
