"""
Base class for search service implementations.
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass
from datetime import datetime


@dataclass
class SearchResult:
    """Data class for search results."""

    title: str
    url: str
    snippet: str
    source: str
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None


class BaseSearchService(ABC):
    """Base class for all search services."""

    def __init__(self, service_name: str, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the search service.

        Args:
            service_name: Name of the service
            config: Service-specific configuration
        """
        self.service_name = service_name
        self.config = config or {}

    @abstractmethod
    async def search(self, query: Union[str, List[str]], **kwargs) -> List[SearchResult]:
        """
        Perform a search query.

        Args:
            query: Search query string
            **kwargs: Additional service-specific parameters

        Returns:
            List of SearchResult objects
        """

    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check if the service is healthy and available.

        Returns:
            True if service is healthy, False otherwise
        """

    def get_service_name(self) -> str:
        """Get the name of this service."""
        return self.service_name
