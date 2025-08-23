#!/bin/bash

# Safecast API Modern - Intelligent Install Script
# Automatically sets up the modernized Safecast API with all dependencies

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
DB_NAME="safecast_modern"
DB_USER="safecast"
DB_PASSWORD="safecast_dev"
ELASTICSEARCH_VERSION="8.11.0"
PYTHON_VERSION="3.11"

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
check_root() {
    if [[ $EUID -eq 0 ]]; then
        log_error "This script should not be run as root"
        exit 1
    fi
}

# Detect operating system
detect_os() {
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        if command -v apt-get &> /dev/null; then
            OS="ubuntu"
            PACKAGE_MANAGER="apt"
        elif command -v yum &> /dev/null; then
            OS="centos"
            PACKAGE_MANAGER="yum"
        elif command -v dnf &> /dev/null; then
            OS="fedora"
            PACKAGE_MANAGER="dnf"
        else
            log_error "Unsupported Linux distribution"
            exit 1
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        OS="macos"
        PACKAGE_MANAGER="brew"
    else
        log_error "Unsupported operating system: $OSTYPE"
        exit 1
    fi
    
    log_info "Detected OS: $OS"
}

# Check if command exists
command_exists() {
    command -v "$1" &> /dev/null
}

# Install system dependencies
install_system_deps() {
    log_info "Installing system dependencies..."
    
    case $OS in
        "ubuntu")
            sudo apt update
            sudo apt install -y \
                python3 python3-pip python3-venv python3-dev \
                postgresql postgresql-contrib postgresql-client \
                postgresql-14-postgis-3 \
                build-essential libpq-dev \
                curl wget git \
                redis-server \
                default-jre  # For Elasticsearch
            ;;
        "macos")
            if ! command_exists brew; then
                log_info "Installing Homebrew..."
                /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
            fi
            
            brew update
            brew install \
                python@${PYTHON_VERSION} \
                postgresql \
                postgis \
                redis \
                openjdk@11
            
            # Start services
            brew services start postgresql
            brew services start redis
            ;;
        "centos"|"fedora")
            if [[ "$OS" == "centos" ]]; then
                sudo yum update -y
                sudo yum install -y epel-release
                sudo yum install -y \
                    python3 python3-pip python3-devel \
                    postgresql postgresql-server postgresql-contrib \
                    postgis \
                    gcc gcc-c++ make \
                    libpq-devel \
                    curl wget git \
                    redis \
                    java-11-openjdk
            else
                sudo dnf update -y
                sudo dnf install -y \
                    python3 python3-pip python3-devel \
                    postgresql postgresql-server postgresql-contrib \
                    postgis \
                    gcc gcc-c++ make \
                    libpq-devel \
                    curl wget git \
                    redis \
                    java-11-openjdk
            fi
            ;;
    esac
    
    log_success "System dependencies installed"
}

# Install Poetry
install_poetry() {
    if ! command_exists poetry; then
        log_info "Installing Poetry..."
        curl -sSL https://install.python-poetry.org | python3 -
        
        # Add Poetry to PATH
        export PATH="$HOME/.local/bin:$PATH"
        echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
        
        log_success "Poetry installed"
    else
        log_info "Poetry already installed"
    fi
}

# Setup PostgreSQL
setup_postgresql() {
    log_info "Setting up PostgreSQL..."
    
    case $OS in
        "ubuntu")
            sudo systemctl start postgresql
            sudo systemctl enable postgresql
            ;;
        "centos"|"fedora")
            sudo postgresql-setup --initdb
            sudo systemctl start postgresql
            sudo systemctl enable postgresql
            ;;
        "macos")
            # Already started by brew services
            ;;
    esac
    
    # Create database and user
    log_info "Creating database and user..."
    
    sudo -u postgres psql -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';" || true
    sudo -u postgres psql -c "CREATE DATABASE $DB_NAME OWNER $DB_USER;" || true
    sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;" || true
    
    # Enable PostGIS extension
    sudo -u postgres psql -d $DB_NAME -c "CREATE EXTENSION IF NOT EXISTS postgis;" || true
    sudo -u postgres psql -d $DB_NAME -c "CREATE EXTENSION IF NOT EXISTS postgis_topology;" || true
    
    log_success "PostgreSQL setup complete"
}

# Install Elasticsearch
install_elasticsearch() {
    log_info "Installing Elasticsearch..."
    
    case $OS in
        "ubuntu")
            # Add Elasticsearch repository
            wget -qO - https://artifacts.elastic.co/GPG-KEY-elasticsearch | sudo apt-key add -
            echo "deb https://artifacts.elastic.co/packages/8.x/apt stable main" | sudo tee /etc/apt/sources.list.d/elastic-8.x.list
            sudo apt update
            sudo apt install -y elasticsearch
            
            # Configure Elasticsearch
            sudo systemctl daemon-reload
            sudo systemctl enable elasticsearch
            sudo systemctl start elasticsearch
            ;;
        "macos")
            brew tap elastic/tap
            brew install elastic/tap/elasticsearch-full
            brew services start elastic/tap/elasticsearch-full
            ;;
        "centos"|"fedora")
            # Add Elasticsearch repository
            sudo rpm --import https://artifacts.elastic.co/GPG-KEY-elasticsearch
            cat << EOF | sudo tee /etc/yum.repos.d/elasticsearch.repo
[elasticsearch]
name=Elasticsearch repository for 8.x packages
baseurl=https://artifacts.elastic.co/packages/8.x/yum
gpgcheck=1
gpgkey=https://artifacts.elastic.co/GPG-KEY-elasticsearch
enabled=0
autorefresh=1
type=rpm-md
EOF
            sudo $PACKAGE_MANAGER install -y --enablerepo=elasticsearch elasticsearch
            sudo systemctl daemon-reload
            sudo systemctl enable elasticsearch
            sudo systemctl start elasticsearch
            ;;
    esac
    
    # Wait for Elasticsearch to start
    log_info "Waiting for Elasticsearch to start..."
    for i in {1..30}; do
        if curl -s http://localhost:9200 &> /dev/null; then
            break
        fi
        sleep 2
    done
    
    log_success "Elasticsearch installed and running"
}

# Setup Python environment
setup_python_env() {
    log_info "Setting up Python environment..."
    
    # Install Poetry dependencies
    poetry install
    
    log_success "Python environment setup complete"
}

# Setup environment configuration
setup_environment() {
    log_info "Setting up environment configuration..."
    
    if [[ ! -f .env ]]; then
        cp .env.example .env
        
        # Generate secret keys
        SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
        JWT_SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
        
        # Update .env file
        sed -i.bak "s|DATABASE_URL=.*|DATABASE_URL=postgresql+asyncpg://$DB_USER:$DB_PASSWORD@localhost:5432/$DB_NAME|g" .env
        sed -i.bak "s|SECRET_KEY=.*|SECRET_KEY=$SECRET_KEY|g" .env
        sed -i.bak "s|JWT_SECRET_KEY=.*|JWT_SECRET_KEY=$JWT_SECRET_KEY|g" .env
        sed -i.bak "s|ELASTICSEARCH_URL=.*|ELASTICSEARCH_URL=http://localhost:9200|g" .env
        
        rm .env.bak
        
        log_success "Environment configuration created"
    else
        log_info "Environment configuration already exists"
    fi
}

# Run database migrations
run_migrations() {
    log_info "Running database migrations..."
    
    # Initialize Alembic if needed
    if [[ ! -d "alembic/versions" ]]; then
        poetry run alembic init alembic
        
        # Update alembic/env.py for our models
        cat > alembic/env.py << 'EOF'
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
import os
import sys

# Add the app directory to the path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from app.core.database import Base
from app.models import *  # Import all models

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
EOF
    fi
    
    # Create initial migration
    poetry run alembic revision --autogenerate -m "Initial migration" || true
    
    # Run migrations
    poetry run alembic upgrade head
    
    log_success "Database migrations complete"
}

# Create sample data
create_sample_data() {
    log_info "Creating sample data..."
    
    cat > create_sample_data.py << 'EOF'
import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from passlib.context import CryptContext
from app.models.user import User
from app.models.device import Device
from app.core.database import Base

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def create_sample_data():
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://safecast:safecast_dev@localhost:5432/safecast_modern")
    
    engine = create_async_engine(DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        # Create admin user
        admin_user = User(
            email="admin@safecast.org",
            name="Admin User",
            hashed_password=pwd_context.hash("admin123"),
            moderator=True,
            confirmed_at=datetime.utcnow()
        )
        session.add(admin_user)
        
        # Create test user
        test_user = User(
            email="test@safecast.org",
            name="Test User",
            hashed_password=pwd_context.hash("test123"),
            confirmed_at=datetime.utcnow()
        )
        session.add(test_user)
        
        await session.commit()
        
        # Create sample device
        device = Device(
            manufacturer="Safecast",
            model="bGeigie Nano",
            sensor="LND7317",
            user_id=test_user.id
        )
        session.add(device)
        
        await session.commit()
        
    print("Sample data created successfully!")
    print("Admin user: admin@safecast.org / admin123")
    print("Test user: test@safecast.org / test123")

if __name__ == "__main__":
    from datetime import datetime
    asyncio.run(create_sample_data())
EOF
    
    poetry run python create_sample_data.py
    rm create_sample_data.py
    
    log_success "Sample data created"
}

# Create startup script
create_startup_script() {
    log_info "Creating startup script..."
    
    cat > start_api.sh << 'EOF'
#!/bin/bash

# Safecast API Modern - Startup Script

# Load environment variables
source .env

# Start services if needed
case "$(uname -s)" in
    Linux*)
        sudo systemctl start postgresql redis-server elasticsearch || true
        ;;
    Darwin*)
        brew services start postgresql redis elasticsearch-full || true
        ;;
esac

# Wait for services
echo "Waiting for services to start..."
sleep 5

# Start the API
echo "Starting Safecast API Modern..."
poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
EOF
    
    chmod +x start_api.sh
    
    log_success "Startup script created"
}

# Health check
health_check() {
    log_info "Running health checks..."
    
    # Check PostgreSQL
    if pg_isready -h localhost -p 5432 &> /dev/null; then
        log_success "PostgreSQL is running"
    else
        log_error "PostgreSQL is not running"
        return 1
    fi
    
    # Check Elasticsearch
    if curl -s http://localhost:9200 &> /dev/null; then
        log_success "Elasticsearch is running"
    else
        log_warning "Elasticsearch is not running (optional for basic functionality)"
    fi
    
    # Check Redis
    if redis-cli ping &> /dev/null; then
        log_success "Redis is running"
    else
        log_warning "Redis is not running (optional for caching)"
    fi
    
    # Check Python environment
    if poetry run python -c "import app.main" &> /dev/null; then
        log_success "Python environment is working"
    else
        log_error "Python environment has issues"
        return 1
    fi
    
    log_success "Health checks passed"
}

# Main installation function
main() {
    echo "=========================================="
    echo "  Safecast API Modern - Install Script"
    echo "=========================================="
    echo
    
    check_root
    detect_os
    
    log_info "Starting installation process..."
    
    # Installation steps
    install_system_deps
    install_poetry
    setup_postgresql
    install_elasticsearch
    setup_python_env
    setup_environment
    run_migrations
    create_sample_data
    create_startup_script
    
    # Final health check
    health_check
    
    echo
    echo "=========================================="
    log_success "Installation completed successfully!"
    echo "=========================================="
    echo
    echo "Next steps:"
    echo "1. Start the API: ./start_api.sh"
    echo "2. Open your browser: http://localhost:8000/docs"
    echo "3. Login with: admin@safecast.org / admin123"
    echo
    echo "Configuration file: .env"
    echo "Documentation: README.md"
    echo "Setup details: SETUP.md"
    echo
}

# Run main function
main "$@"
