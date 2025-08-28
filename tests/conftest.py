import os
import sys
from unittest.mock import Mock
import sqlalchemy.ext.asyncio as sa_asyncio

# Ensure the app package is importable
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Provide a dummy database URL and avoid creating real engines during import
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
sa_asyncio.create_async_engine = Mock(return_value=None)
