"""
Small reusable SQLAlchemy type helpers.

`JSONList` stores a Python list of strings as JSON. Using the generic `JSON`
type keeps the models portable across the sqlite (dev) and PostgreSQL (prod)
backends without dialect-specific columns.
"""

from sqlalchemy import JSON
from sqlalchemy.types import TypeDecorator


class JSONList(TypeDecorator):
    """A JSON column that always defaults to an empty list rather than NULL."""

    impl = JSON
    cache_ok = True

    def process_bind_param(self, value, dialect):
        return value if value is not None else []

    def process_result_value(self, value, dialect):
        return value if value is not None else []
