#!/usr/bin/env python3
"""
Safecast API Modern - Intelligent Python Install Script
Cross-platform installer with interactive setup and validation
"""

import os
import sys
import subprocess
import platform
import shutil
import json
import time
import urllib.request
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Colors for terminal output
class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    PURPLE = '\033[0;35m'
    CYAN = '\033[0;36m'
    WHITE = '\033[1;37m'
    BOLD = '\033[1m'
    NC = '\033[0m'  # No Color

class Logger:
    @staticmethod
    def info(msg: str):
        print(f"{Colors.BLUE}[INFO]{Colors.NC} {msg}")
    
    @staticmethod
    def success(msg: str):
        print(f"{Colors.GREEN}[SUCCESS]{Colors.NC} {msg}")
    
    @staticmethod
    def warning(msg: str):
        print(f"{Colors.YELLOW}[WARNING]{Colors.NC} {msg}")
    
    @staticmethod
    def error(msg: str):
        print(f"{Colors.RED}[ERROR]{Colors.NC} {msg}")
    
    @staticmethod
    def step(msg: str):
        print(f"{Colors.CYAN}[STEP]{Colors.NC} {msg}")

class SystemInfo:
    def __init__(self):
        self.os_type = platform.system().lower()
        self.arch = platform.machine().lower()
        self.python_version = sys.version_info
        self.is_admin = self._check_admin()
        
    def _check_admin(self) -> bool:
        try:
            return os.getuid() == 0
        except AttributeError:
            import ctypes
            return ctypes.windll.shell32.IsUserAnAdmin() != 0

class DependencyChecker:
    def __init__(self):
        self.required_commands = {
            'python3': 'Python 3.11+',
            'git': 'Git version control',
            'curl': 'HTTP client',
        }
        self.optional_commands = {
            'docker': 'Docker (optional)',
            'docker-compose': 'Docker Compose (optional)',
        }
    
    def check_command(self, command: str) -> bool:
        return shutil.which(command) is not None
    
    def check_python_version(self) -> bool:
        return sys.version_info >= (3, 11)
    
    def check_all(self) -> Dict[str, bool]:
        results = {}
        
        # Check required commands
        for cmd, desc in self.required_commands.items():
            exists = self.check_command(cmd)
            results[cmd] = exists
            if exists:
                Logger.success(f"{desc} ✓")
            else:
                Logger.error(f"{desc} ✗")
        
        # Check Python version specifically
        if self.check_python_version():
            Logger.success(f"Python {sys.version_info.major}.{sys.version_info.minor} ✓")
        else:
            Logger.error(f"Python 3.11+ required, found {sys.version_info.major}.{sys.version_info.minor} ✗")
            results['python_version'] = False
        
        # Check optional commands
        for cmd, desc in self.optional_commands.items():
            exists = self.check_command(cmd)
            if exists:
                Logger.info(f"{desc} ✓")
            else:
                Logger.info(f"{desc} (not installed)")
        
        return results

class PackageManager:
    def __init__(self, os_type: str):
        self.os_type = os_type
        self.manager = self._detect_package_manager()
    
    def _detect_package_manager(self) -> Optional[str]:
        if self.os_type == 'linux':
            if shutil.which('apt'):
                return 'apt'
            elif shutil.which('yum'):
                return 'yum'
            elif shutil.which('dnf'):
                return 'dnf'
            elif shutil.which('pacman'):
                return 'pacman'
        elif self.os_type == 'darwin':
            return 'brew'
        elif self.os_type == 'windows':
            return 'choco'
        return None
    
    def install_packages(self, packages: List[str]) -> bool:
        if not self.manager:
            Logger.error("No supported package manager found")
            return False
        
        Logger.info(f"Installing packages with {self.manager}: {', '.join(packages)}")
        
        try:
            if self.manager == 'apt':
                subprocess.run(['sudo', 'apt', 'update'], check=True)
                subprocess.run(['sudo', 'apt', 'install', '-y'] + packages, check=True)
            elif self.manager == 'brew':
                subprocess.run(['brew', 'install'] + packages, check=True)
            elif self.manager in ['yum', 'dnf']:
                subprocess.run(['sudo', self.manager, 'install', '-y'] + packages, check=True)
            elif self.manager == 'pacman':
                subprocess.run(['sudo', 'pacman', '-S', '--noconfirm'] + packages, check=True)
            elif self.manager == 'choco':
                subprocess.run(['choco', 'install', '-y'] + packages, check=True)
            
            return True
        except subprocess.CalledProcessError as e:
            Logger.error(f"Failed to install packages: {e}")
            return False

class DatabaseSetup:
    def __init__(self, os_type: str):
        self.os_type = os_type
        self.db_name = "safecast_modern"
        self.db_user = "safecast"
        self.db_password = "safecast_dev"
    
    def install_postgresql(self, pkg_manager: PackageManager) -> bool:
        Logger.step("Installing PostgreSQL with PostGIS...")
        
        packages = []
        if pkg_manager.manager == 'apt':
            # Detect PostgreSQL version dynamically
            try:
                result = subprocess.run(['apt-cache', 'policy', 'postgresql'], 
                                      capture_output=True, text=True, check=True)
                for line in result.stdout.split('\n'):
                    if 'Candidate:' in line:
                        pg_version = line.split(':')[1].split('+')[0].strip()
                        break
                else:
                    pg_version = '16'  # Default fallback
                
                postgis_package = f'postgresql-{pg_version}-postgis-3'
                packages = ['postgresql', 'postgresql-contrib', postgis_package]
            except subprocess.CalledProcessError:
                # Fallback to generic PostGIS metapackage
                packages = ['postgresql', 'postgresql-contrib', 'postgresql-postgis']
        elif pkg_manager.manager == 'brew':
            packages = ['postgresql', 'postgis']
        elif pkg_manager.manager in ['yum', 'dnf']:
            packages = ['postgresql', 'postgresql-server', 'postgresql-contrib', 'postgis']
        elif pkg_manager.manager == 'pacman':
            packages = ['postgresql', 'postgis']
        
        if not packages:
            Logger.error("Unsupported package manager for PostgreSQL installation")
            return False
        
        return pkg_manager.install_packages(packages)
    
    def setup_database(self) -> bool:
        Logger.step("Setting up PostgreSQL database...")
        
        try:
            # Start PostgreSQL service
            if self.os_type == 'linux':
                subprocess.run(['sudo', 'systemctl', 'start', 'postgresql'], check=True)
                subprocess.run(['sudo', 'systemctl', 'enable', 'postgresql'], check=True)
            elif self.os_type == 'darwin':
                subprocess.run(['brew', 'services', 'start', 'postgresql'], check=True)
            
            # Create database and user
            commands = [
                f"CREATE USER {self.db_user} WITH PASSWORD '{self.db_password}';",
                f"CREATE DATABASE {self.db_name} OWNER {self.db_user};",
                f"GRANT ALL PRIVILEGES ON DATABASE {self.db_name} TO {self.db_user};",
            ]
            
            for cmd in commands:
                try:
                    subprocess.run(['sudo', '-u', 'postgres', 'psql', '-c', cmd], 
                                 check=True, capture_output=True)
                except subprocess.CalledProcessError:
                    # Command might fail if already exists
                    pass
            
            # Enable PostGIS extension
            postgis_commands = [
                "CREATE EXTENSION IF NOT EXISTS postgis;",
                "CREATE EXTENSION IF NOT EXISTS postgis_topology;",
            ]
            
            for cmd in postgis_commands:
                try:
                    subprocess.run(['sudo', '-u', 'postgres', 'psql', '-d', self.db_name, '-c', cmd],
                                 check=True, capture_output=True)
                except subprocess.CalledProcessError:
                    pass
            
            Logger.success("PostgreSQL database setup complete")
            return True
            
        except subprocess.CalledProcessError as e:
            Logger.error(f"Failed to setup PostgreSQL: {e}")
            return False

class ElasticsearchSetup:
    def __init__(self, os_type: str):
        self.os_type = os_type
        self.version = "8.11.0"
    
    def install(self, pkg_manager: PackageManager) -> bool:
        Logger.step("Installing Elasticsearch...")
        
        try:
            if pkg_manager.manager == 'apt':
                # Add Elasticsearch repository
                subprocess.run(['wget', '-qO', '-', 'https://artifacts.elastic.co/GPG-KEY-elasticsearch'], 
                             stdout=subprocess.PIPE, check=True)
                subprocess.run(['sudo', 'apt-key', 'add', '-'], 
                             input=subprocess.run(['wget', '-qO', '-', 'https://artifacts.elastic.co/GPG-KEY-elasticsearch'], 
                                                 stdout=subprocess.PIPE, check=True).stdout, check=True)
                
                with open('/tmp/elastic.list', 'w') as f:
                    f.write("deb https://artifacts.elastic.co/packages/8.x/apt stable main\n")
                subprocess.run(['sudo', 'mv', '/tmp/elastic.list', '/etc/apt/sources.list.d/elastic-8.x.list'], check=True)
                subprocess.run(['sudo', 'apt', 'update'], check=True)
                subprocess.run(['sudo', 'apt', 'install', '-y', 'elasticsearch'], check=True)
                
            elif pkg_manager.manager == 'brew':
                subprocess.run(['brew', 'tap', 'elastic/tap'], check=True)
                subprocess.run(['brew', 'install', 'elastic/tap/elasticsearch-full'], check=True)
                
            else:
                Logger.warning("Elasticsearch auto-install not supported for this OS. Please install manually.")
                return False
            
            # Start Elasticsearch
            if self.os_type == 'linux':
                subprocess.run(['sudo', 'systemctl', 'enable', 'elasticsearch'], check=True)
                subprocess.run(['sudo', 'systemctl', 'start', 'elasticsearch'], check=True)
            elif self.os_type == 'darwin':
                subprocess.run(['brew', 'services', 'start', 'elastic/tap/elasticsearch-full'], check=True)
            
            # Wait for Elasticsearch to start
            Logger.info("Waiting for Elasticsearch to start...")
            for i in range(30):
                try:
                    urllib.request.urlopen('http://localhost:9200', timeout=2)
                    Logger.success("Elasticsearch is running")
                    return True
                except:
                    time.sleep(2)
            
            Logger.warning("Elasticsearch may not be running properly")
            return False
            
        except subprocess.CalledProcessError as e:
            Logger.error(f"Failed to install Elasticsearch: {e}")
            return False

class PythonEnvironment:
    def __init__(self):
        self.poetry_installed = shutil.which('poetry') is not None
    
    def install_poetry(self) -> bool:
        if self.poetry_installed:
            Logger.info("Poetry already installed")
            return True
        
        Logger.step("Installing Poetry...")
        try:
            # Download and install Poetry
            subprocess.run([
                'curl', '-sSL', 'https://install.python-poetry.org'
            ], stdout=subprocess.PIPE, check=True)
            
            install_script = subprocess.run([
                'curl', '-sSL', 'https://install.python-poetry.org'
            ], stdout=subprocess.PIPE, check=True).stdout
            
            subprocess.run(['python3'], input=install_script, check=True)
            
            # Add Poetry to PATH
            poetry_bin = Path.home() / '.local' / 'bin'
            current_path = os.environ.get('PATH', '')
            if str(poetry_bin) not in current_path:
                os.environ['PATH'] = f"{poetry_bin}:{current_path}"
            
            Logger.success("Poetry installed")
            return True
            
        except subprocess.CalledProcessError as e:
            Logger.error(f"Failed to install Poetry: {e}")
            return False
    
    def setup_project(self) -> bool:
        Logger.step("Setting up Python project environment...")
        try:
            subprocess.run(['poetry', 'install'], check=True)
            Logger.success("Python dependencies installed")
            return True
        except subprocess.CalledProcessError as e:
            Logger.error(f"Failed to install Python dependencies: {e}")
            return False

class ConfigurationManager:
    def __init__(self):
        self.env_file = Path('.env')
        self.env_example = Path('.env.example')
    
    def setup_environment(self, db_config: Dict[str, str]) -> bool:
        Logger.step("Setting up environment configuration...")
        
        if self.env_file.exists():
            Logger.info("Environment file already exists")
            return True
        
        if not self.env_example.exists():
            Logger.error(".env.example file not found")
            return False
        
        # Copy example to .env
        shutil.copy(self.env_example, self.env_file)
        
        # Generate secret keys
        import secrets
        secret_key = secrets.token_urlsafe(32)
        jwt_secret = secrets.token_urlsafe(32)
        
        # Read and update .env file
        with open(self.env_file, 'r') as f:
            content = f.read()
        
        # Replace placeholders
        replacements = {
            'DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/safecast_modern':
                f"DATABASE_URL=postgresql+asyncpg://{db_config['user']}:{db_config['password']}@localhost:5432/{db_config['name']}",
            'SECRET_KEY=your-secret-key-here': f"SECRET_KEY={secret_key}",
            'JWT_SECRET_KEY=your-jwt-secret-here': f"JWT_SECRET_KEY={jwt_secret}",
            'ELASTICSEARCH_URL=http://localhost:9200': 'ELASTICSEARCH_URL=http://localhost:9200',
        }
        
        for old, new in replacements.items():
            content = content.replace(old, new)
        
        with open(self.env_file, 'w') as f:
            f.write(content)
        
        Logger.success("Environment configuration created")
        return True

class DatabaseMigration:
    def __init__(self):
        pass
    
    def run_migrations(self) -> bool:
        Logger.step("Running database migrations...")
        try:
            # Check if alembic is initialized
            if not Path('alembic').exists():
                subprocess.run(['poetry', 'run', 'alembic', 'init', 'alembic'], check=True)
                self._setup_alembic_env()
            
            # Create initial migration
            try:
                subprocess.run(['poetry', 'run', 'alembic', 'revision', '--autogenerate', '-m', 'Initial migration'], 
                             check=True, capture_output=True)
            except subprocess.CalledProcessError:
                pass  # Migration might already exist
            
            # Run migrations
            subprocess.run(['poetry', 'run', 'alembic', 'upgrade', 'head'], check=True)
            
            Logger.success("Database migrations completed")
            return True
            
        except subprocess.CalledProcessError as e:
            Logger.error(f"Failed to run migrations: {e}")
            return False
    
    def _setup_alembic_env(self):
        """Setup alembic/env.py with proper model imports"""
        env_content = '''from logging.config import fileConfig
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
'''
        with open('alembic/env.py', 'w') as f:
            f.write(env_content)

class HealthChecker:
    def __init__(self):
        pass
    
    def check_all(self) -> bool:
        Logger.step("Running health checks...")
        
        all_good = True
        
        # Check PostgreSQL
        try:
            subprocess.run(['pg_isready', '-h', 'localhost', '-p', '5432'], 
                         check=True, capture_output=True)
            Logger.success("PostgreSQL ✓")
        except (subprocess.CalledProcessError, FileNotFoundError):
            Logger.error("PostgreSQL ✗")
            all_good = False
        
        # Check Elasticsearch
        try:
            urllib.request.urlopen('http://localhost:9200', timeout=5)
            Logger.success("Elasticsearch ✓")
        except:
            Logger.warning("Elasticsearch ✗ (optional)")
        
        # Check Python environment
        try:
            subprocess.run(['poetry', 'run', 'python', '-c', 'import app.main'], 
                         check=True, capture_output=True)
            Logger.success("Python environment ✓")
        except subprocess.CalledProcessError:
            Logger.error("Python environment ✗")
            all_good = False
        
        return all_good

class SafecastInstaller:
    def __init__(self):
        self.system_info = SystemInfo()
        self.dependency_checker = DependencyChecker()
        self.package_manager = PackageManager(self.system_info.os_type)
        self.db_setup = DatabaseSetup(self.system_info.os_type)
        self.es_setup = ElasticsearchSetup(self.system_info.os_type)
        self.python_env = PythonEnvironment()
        self.config_manager = ConfigurationManager()
        self.db_migration = DatabaseMigration()
        self.health_checker = HealthChecker()
    
    def print_banner(self):
        print(f"""
{Colors.CYAN}{'='*60}{Colors.NC}
{Colors.BOLD}    Safecast API Modern - Intelligent Installer{Colors.NC}
{Colors.CYAN}{'='*60}{Colors.NC}

{Colors.WHITE}System Information:{Colors.NC}
- OS: {self.system_info.os_type.title()} ({self.system_info.arch})
- Python: {self.system_info.python_version.major}.{self.system_info.python_version.minor}.{self.system_info.python_version.micro}
- Package Manager: {self.package_manager.manager or 'None detected'}

""")
    
    def interactive_setup(self) -> Dict[str, any]:
        """Interactive configuration setup"""
        print(f"{Colors.YELLOW}Configuration Setup{Colors.NC}")
        print("Press Enter to use default values in [brackets]\n")
        
        config = {}
        
        # Database configuration
        config['db_name'] = input(f"Database name [{self.db_setup.db_name}]: ").strip() or self.db_setup.db_name
        config['db_user'] = input(f"Database user [{self.db_setup.db_user}]: ").strip() or self.db_setup.db_user
        config['db_password'] = input(f"Database password [{self.db_setup.db_password}]: ").strip() or self.db_setup.db_password
        
        # Installation options
        config['install_elasticsearch'] = input("Install Elasticsearch? [y/N]: ").strip().lower() in ['y', 'yes']
        config['create_sample_data'] = input("Create sample data? [Y/n]: ").strip().lower() not in ['n', 'no']
        
        return config
    
    def install(self, interactive: bool = True):
        self.print_banner()
        
        # Check if running as root
        if self.system_info.is_admin:
            Logger.error("Do not run this installer as root/administrator")
            sys.exit(1)
        
        # Interactive configuration
        config = {}
        if interactive:
            config = self.interactive_setup()
        else:
            config = {
                'db_name': self.db_setup.db_name,
                'db_user': self.db_setup.db_user,
                'db_password': self.db_setup.db_password,
                'install_elasticsearch': True,
                'create_sample_data': True,
            }
        
        # Update configuration
        self.db_setup.db_name = config['db_name']
        self.db_setup.db_user = config['db_user']
        self.db_setup.db_password = config['db_password']
        
        print(f"\n{Colors.CYAN}Starting installation...{Colors.NC}\n")
        
        # Step 1: Check dependencies
        Logger.step("Checking system dependencies...")
        deps_ok = self.dependency_checker.check_all()
        if not all(deps_ok.values()):
            Logger.error("Missing required dependencies. Please install them manually.")
            return False
        
        # Step 2: Install PostgreSQL
        if not self.db_setup.install_postgresql(self.package_manager):
            Logger.error("Failed to install PostgreSQL")
            return False
        
        if not self.db_setup.setup_database():
            Logger.error("Failed to setup database")
            return False
        
        # Step 3: Install Elasticsearch (optional)
        if config['install_elasticsearch']:
            self.es_setup.install(self.package_manager)
        
        # Step 4: Setup Python environment
        if not self.python_env.install_poetry():
            Logger.error("Failed to install Poetry")
            return False
        
        if not self.python_env.setup_project():
            Logger.error("Failed to setup Python project")
            return False
        
        # Step 5: Configure environment
        db_config = {
            'name': config['db_name'],
            'user': config['db_user'],
            'password': config['db_password']
        }
        if not self.config_manager.setup_environment(db_config):
            Logger.error("Failed to setup environment configuration")
            return False
        
        # Step 6: Run migrations
        if not self.db_migration.run_migrations():
            Logger.error("Failed to run database migrations")
            return False
        
        # Step 7: Create sample data
        if config['create_sample_data']:
            self.create_sample_data()
        
        # Step 8: Create startup script
        self.create_startup_script()
        
        # Step 9: Health check
        if not self.health_checker.check_all():
            Logger.warning("Some health checks failed, but installation may still work")
        
        # Success message
        print(f"""
{Colors.GREEN}{'='*60}{Colors.NC}
{Colors.BOLD}    Installation completed successfully!{Colors.NC}
{Colors.GREEN}{'='*60}{Colors.NC}

{Colors.WHITE}Next steps:{Colors.NC}
1. Start the API: {Colors.CYAN}./start_api.sh{Colors.NC}
2. Open browser: {Colors.CYAN}http://localhost:8000/docs{Colors.NC}
3. Login with: {Colors.CYAN}admin@safecast.org / admin123{Colors.NC}

{Colors.WHITE}Files created:{Colors.NC}
- Configuration: {Colors.CYAN}.env{Colors.NC}
- Startup script: {Colors.CYAN}start_api.sh{Colors.NC}
- Documentation: {Colors.CYAN}README.md{Colors.NC}

{Colors.WHITE}Useful commands:{Colors.NC}
- Start API: {Colors.CYAN}poetry run uvicorn app.main:app --reload{Colors.NC}
- Run tests: {Colors.CYAN}poetry run pytest{Colors.NC}
- Database shell: {Colors.CYAN}psql -h localhost -U {config['db_user']} -d {config['db_name']}{Colors.NC}

""")
        return True
    
    def create_sample_data(self):
        Logger.step("Creating sample data...")
        
        sample_script = '''
import asyncio
import os
from datetime import datetime
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from passlib.context import CryptContext
from app.models.user import User
from app.models.device import Device

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def create_sample_data():
    DATABASE_URL = os.getenv("DATABASE_URL")
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
        await session.refresh(admin_user)
        await session.refresh(test_user)
        
        # Create sample device
        device = Device(
            manufacturer="Safecast",
            model="bGeigie Nano",
            sensor="LND7317",
            user_id=test_user.id
        )
        session.add(device)
        await session.commit()
        
    print("Sample data created!")

if __name__ == "__main__":
    asyncio.run(create_sample_data())
'''
        
        with open('create_sample_data.py', 'w') as f:
            f.write(sample_script)
        
        try:
            subprocess.run(['poetry', 'run', 'python', 'create_sample_data.py'], check=True)
            os.remove('create_sample_data.py')
            Logger.success("Sample data created")
        except subprocess.CalledProcessError:
            Logger.warning("Failed to create sample data")
    
    def create_startup_script(self):
        Logger.step("Creating startup script...")
        
        startup_script = '''#!/bin/bash
# Safecast API Modern - Startup Script

set -e

# Colors
GREEN='\\033[0;32m'
BLUE='\\033[0;34m'
NC='\\033[0m'

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
'''
        
        with open('start_api.sh', 'w') as f:
            f.write(startup_script)
        
        os.chmod('start_api.sh', 0o755)
        Logger.success("Startup script created")

def main():
    installer = SafecastInstaller()
    
    # Parse command line arguments
    interactive = '--non-interactive' not in sys.argv
    
    try:
        success = installer.install(interactive=interactive)
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Installation cancelled by user{Colors.NC}")
        sys.exit(1)
    except Exception as e:
        Logger.error(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
