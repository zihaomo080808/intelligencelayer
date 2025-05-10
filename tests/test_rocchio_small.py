"""
Test script for the Rocchio algorithm implementation and feedback system.
Using small dimensions for testing.
"""
import sys
import os
import asyncio
import json
import numpy as np
from pathlib import Path

# Add project root to system path for imports
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))

from feedback.rocchio import RocchioUpdater
from database.session import AsyncSessionLocal, get_db
from database.models import UserProfile, UserFeedback
from profiles.profiles import get_profile, update_profile, record_feedback, update_user_embedding

async def test_rocchio_algorithm():
    """Test the Rocchio algorithm directly."""
    print("Testing Rocchio algorithm directly...")
    
    # Create a Rocchio updater
    rocchio = RocchioUpdater(alpha=0.8, beta=0.2, gamma=0.1)
    
    # Create some test embeddings (small dimension for testing)
    original = [0.1, 0.2, 0.3, 0.4, 0.5]
    relevant = [
        [0.2, 0.3, 0.4, 0.5, 0.6],
        [0.3, 0.4, 0.5, 0.6, 0.7]
    ]
    non_relevant = [
        [0.6, 0.5, 0.4, 0.3, 0.2],
        [0.7, 0.6, 0.5, 0.4, 0.3]
    ]
    
    # Update embedding
    updated = rocchio.update_embedding(original, relevant, non_relevant)
    
    # Print results
    print(f"Original: {original}")
    print(f"Updated:  {updated}")
    
    # Check that the embedding has been updated
    assert len(updated) == len(original)
    assert updated != original
    print("Rocchio algorithm test passed!\n")
    
    return updated

async def test_database_operations():
    """Test the database operations for the feedback system."""
    print("Testing database operations...")
    
    user_id = "test_user_rocchio"
    
    async with AsyncSessionLocal() as db:
        # Create or update user profile with small test embedding
        embedding = [0.1, 0.2, 0.3, 0.4, 0.5]
        profile = await update_profile(
            user_id=user_id,
            bio="Test user for Rocchio algorithm",
            stances={"ai": 0.8, "climate": 0.6},
            embedding=embedding,
            db=db
        )
        
        print(f"Profile created: {profile.user_id}")
        
        # Create some test items with small embeddings
        items = [
            {
                "id": "item1",
                "embedding": [0.2, 0.3, 0.4, 0.5, 0.6]
            },
            {
                "id": "item2", 
                "embedding": [0.6, 0.5, 0.4, 0.3, 0.2]
            }
        ]
        
        # Record feedback for the items
        print("Recording feedback...")
        await record_feedback(
            db=db,
            user_id=user_id,
            item_id=items[0]["id"],
            feedback_type="like",
            item_embedding=items[0]["embedding"]
        )
        
        await record_feedback(
            db=db,
            user_id=user_id,
            item_id=items[1]["id"],
            feedback_type="skip",
            item_embedding=items[1]["embedding"]
        )
        
        # Get the updated profile
        updated_profile = await get_profile(user_id, db)
        if updated_profile.embedding is not None:
            print(f"Updated embedding: {updated_profile.embedding[:5]}...")
        
        # Check that the embedding has been updated
        assert updated_profile.embedding is not None
        
        if isinstance(updated_profile.embedding, np.ndarray):
            original_embedding = np.array(embedding)
            assert not np.array_equal(updated_profile.embedding[:5], original_embedding)
        else:
            assert updated_profile.embedding != embedding
            
        print("Database operations test passed!\n")
        
        # Clean up - Remove test data
        print("Cleaning up test data...")
        await db.execute("DELETE FROM user_feedback WHERE user_id = :user_id", {"user_id": user_id})
        await db.execute("DELETE FROM user_item_interactions WHERE user_id = :user_id", {"user_id": user_id})
        await db.execute("DELETE FROM profiles WHERE user_id = :user_id", {"user_id": user_id})
        await db.commit()
        print("Test data cleaned up")

async def main():
    """Run all tests."""
    print("=== Testing Rocchio Algorithm and Feedback System ===")
    
    # Test the Rocchio algorithm directly
    await test_rocchio_algorithm()
    
    # Test database operations
    await test_database_operations()
    
    print("All tests completed successfully!")

if __name__ == "__main__":
    asyncio.run(main())