#!/usr/bin/env python3
"""
Create demo users for testing approval functionality
"""
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db_session
from app.models.user import User
from app.core.security import get_password_hash

async def create_demo_users():
    """Create demo users for testing"""
    async with get_db_session() as db:
        # Check if users already exist
        existing_users = await db.execute(select(User))
        if existing_users.scalars().first():
            print("Demo users already exist")
            return
        
        # Create demo users
        users = [
            {
                "email": "admin@safecast.org",
                "name": "Admin User",
                "password": "admin123",
                "moderator": True
            },
            {
                "email": "moderator@safecast.org", 
                "name": "Moderator User",
                "password": "mod123",
                "moderator": True
            },
            {
                "email": "user@safecast.org",
                "name": "Regular User", 
                "password": "user123",
                "moderator": False
            }
        ]
        
        for user_data in users:
            user = User(
                email=user_data["email"],
                name=user_data["name"],
                hashed_password=get_password_hash(user_data["password"]),
                moderator=user_data["moderator"],
                confirmed_at=asyncio.get_event_loop().time()  # Mark as confirmed
            )
            db.add(user)
        
        await db.commit()
        print("Demo users created successfully!")
        print("- admin@safecast.org / admin123 (Admin)")
        print("- moderator@safecast.org / mod123 (Moderator)")
        print("- user@safecast.org / user123 (Regular User)")

if __name__ == "__main__":
    asyncio.run(create_demo_users())
