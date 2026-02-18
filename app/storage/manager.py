import os
import threading
from app.core.config import STORAGE_MODE
from .interface import FileStorageInterface, VectorStorageInterface, MetadataStorageInterface
from app.core.logging import log_info, log_error

class StorageManager:
    _instance = None
    _lock = threading.Lock()

    def __init__(self):
        self.mode = STORAGE_MODE
        self._files = None
        self._vectors = None
        self._metadata = None
        # Do not initialize adapters immediately to avoid import-time I/O or errors
        # self._initialize_adapters()

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def _ensure_initialized(self):
        """Ensure all adapters are initialized for the current mode."""
        if self._files and self._vectors and self._metadata:
            return

        with self._lock:
            if self._files and self._vectors and self._metadata:
                return
                
            log_info(f"Initializing StorageManager in {self.mode} mode")
            try:
                # Initialize one by one or all
                if not self._files:
                    self._files = self._init_files()
                if not self._vectors:
                    self._vectors = self._init_vectors()
                if not self._metadata:
                    self._metadata = self._init_metadata()
                log_info("Storage adapters initialized successfully")
            except Exception as e:
                log_error(f"Failed to initialize storage adapters: {e}")
                # We might want to raise, or leave in partial state. 
                # Raising here means first access fails.
                raise

    def reinitialize(self, mode: str):
        """
        Re-initialize the storage manager with a new mode.
        This is thread-safe.
        """
        with self._lock:
            log_info(f"Switching storage mode from {self.mode} to {mode}")
            self.mode = mode
            self._files = None
            self._vectors = None
            self._metadata = None
            # Lazy init will happen on next access
            # or we can force it:
            # self._ensure_initialized() 

    @property
    def state(self) -> str:
        if not (self._files and self._vectors and self._metadata):
            return "INITIALIZING"
        if self.mode == "local":
            return "ACTIVE_LOCAL"
        if self.mode == "aws":
            return "ACTIVE_AWS"
        return "UNKNOWN"

    def get_status(self) -> dict:
        """
        Get comprehensive status of the storage system.
        """
        return {
            "mode": self.mode,
            "state": self.state,
            "adapters": {
                "files": {
                    "type": self._files.__class__.__name__ if self._files else "Not Initialized",
                    "status": "connected" if self._files else "pending"
                },
                "vectors": {
                    "type": self._vectors.__class__.__name__ if self._vectors else "Not Initialized",
                    "status": "connected" if self._vectors else "pending"
                },
                "metadata": {
                    "type": self._metadata.__class__.__name__ if self._metadata else "Not Initialized",
                    "status": "connected" if self._metadata else "pending"
                }
            }
        }

    @property
    def files(self) -> FileStorageInterface:
        self._ensure_initialized()
        return self._files

    @property
    def vectors(self) -> VectorStorageInterface:
        self._ensure_initialized()
        return self._vectors

    @property
    def metadata(self) -> MetadataStorageInterface:
        self._ensure_initialized()
        return self._metadata

    def _init_files(self) -> FileStorageInterface:
        if self.mode == "aws":
            from .files import S3FileStorage
            return S3FileStorage()
        else:
            from .files import LocalFileStorage
            return LocalFileStorage()

    def _init_vectors(self) -> VectorStorageInterface:
        if self.mode == "aws":
            from .vectors import PineconeVectorStorage
            return PineconeVectorStorage()
        else:
            from .vectors import ChromaVectorStorage
            return ChromaVectorStorage()

    def _init_metadata(self) -> MetadataStorageInterface:
        if self.mode == "aws":
            from .metadata import CloudMetadataStorage
            return CloudMetadataStorage() 
        else:
            from .metadata import LocalMetadataStorage
            return LocalMetadataStorage()

storage_manager = StorageManager.get_instance()
