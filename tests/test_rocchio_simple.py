"""
Simplified test script for the Rocchio algorithm implementation.
"""
import sys
from pathlib import Path
import numpy as np

# Add project root to system path for imports
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))

from feedback.rocchio import RocchioUpdater

def test_rocchio_algorithm():
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
    print("Rocchio algorithm test passed!")
    
    return updated

if __name__ == "__main__":
    test_rocchio_algorithm()