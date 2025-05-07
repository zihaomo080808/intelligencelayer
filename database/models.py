"""
Shared database models used across the application.
This file should import and re-export all models from various parts of the application
to provide a central reference point.
"""

# Import Base for model definitions
from .base import Base

# Import specific models from profiles
from profiles.profiles import UserProfile

# Re-export all models
__all__ = [
    "UserProfile",
    # Add other models as they are created
]
