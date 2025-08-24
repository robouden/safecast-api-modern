#!/bin/bash
# Safecast API Modern - Startup Script

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}Starting Safecast API Modern...${NC}"

# Load environment
if [[ -f .env ]]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Start services based on OS
case "$(uname -s)" in
    Linux*)
        echo "Starting services on Linux..."
        sudo systemctl start postgresql || true
        sudo systemctl start elasticsearch || true
        sudo systemctl start redis-server || true
        ;;
    Darwin*)
        echo "Starting services on macOS..."
        brew services start postgresql || true
        brew services start elasticsearch-full || true
        brew services start redis || true
        ;;
esac

# Wait for services
echo "Waiting for services to start..."
sleep 3

# Check PostgreSQL
if pg_isready -h localhost -p 5432 >/dev/null 2>&1; then
    echo -e "${GREEN}PostgreSQL is ready${NC}"
else
    echo "Warning: PostgreSQL may not be running"
fi

# Start the API
echo -e "${GREEN}Starting Safecast API...${NC}"
echo "API will be available at: http://localhost:8000"
echo "Documentation: http://localhost:8000/docs"
echo "Press Ctrl+C to stop"
echo

poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
