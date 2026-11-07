"""Base document model and helpers for MongoDB."""

from datetime import datetime, timezone
from typing import Any, Dict, Optional


def utc_now() -> datetime:
    """Returns current datetime in UTC timezone."""
    return datetime.now(timezone.utc)


class BaseDoc:
    """Base class for domain models stored in MongoDB collections."""

    def to_dict(self) -> Dict[str, Any]:
        """Serializes document to a dictionary suitable for MongoDB."""
        d = dict(self.__dict__)
        return d

    @classmethod
    def from_doc(cls, doc: Optional[Dict[str, Any]]):
        """Constructs an instance from a MongoDB document."""
        if doc is None:
            return None
        # Exclude MongoDB internal _id if model has id field
        data = {k: v for k, v in doc.items() if k != "_id"}
        return cls(**data)
