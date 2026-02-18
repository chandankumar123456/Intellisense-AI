from abc import ABC, abstractmethod
from typing import BinaryIO, List, Dict, Any, Optional

class FileStorageInterface(ABC):
    @abstractmethod
    def save_file(self, path: str, content: bytes, content_type: str = "application/octet-stream") -> str:
        """Save a file and return its storage path/identifier."""
        pass

    @abstractmethod
    def read_file(self, path: str) -> bytes:
        """Read a file's content."""
        pass

    @abstractmethod
    def delete_file(self, path: str) -> None:
        """Delete a file."""
        pass
    
    @abstractmethod
    def exists(self, path: str) -> bool:
        """Check if file exists."""
        pass

class VectorStorageInterface(ABC):
    @abstractmethod
    def upsert(self, vectors: List[Dict[str, Any]], namespace: str = "") -> None:
        """Upsert vectors with metadata."""
        pass

    @abstractmethod
    def query(self, vector: List[float], top_k: int = 10, namespace: str = "", filter: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """Query vectors."""
        pass

    @abstractmethod
    def delete(self, ids: List[str], namespace: str = "") -> None:
        """Delete vectors by ID."""
        pass

class MetadataStorageInterface(ABC):
    @abstractmethod
    def upsert(self, metadata: Dict[str, Any]) -> None:
        """Upsert a single metadata record."""
        pass

    @abstractmethod
    def upsert_batch(self, metadata_list: List[Dict[str, Any]]) -> None:
        """Batched upsert of metadata."""
        pass

    @abstractmethod
    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Get metadata by primary key/ID."""
        pass

    @abstractmethod
    def search(self, filters: Dict[str, Any], limit: int = 10) -> List[Dict[str, Any]]:
        """Search metadata with filters."""
        pass
