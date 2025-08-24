
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
