"""Profile repository — delegates to UserRepository."""

# The user_repo.py handles all profile operations.
# This module exists for structural completeness and potential future separation.

from storage.repositories.user_repo import UserRepository

ProfileRepository = UserRepository
