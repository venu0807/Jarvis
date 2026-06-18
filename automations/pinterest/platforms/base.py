"""
Base Platform Abstraction
All platforms implement this interface.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class PostStatus(Enum):
    SUCCESS = "success"
    FAILED = "failed"
    PENDING = "pending"
    RATE_LIMITED = "rate_limited"
    AUTH_ERROR = "auth_error"


@dataclass
class MediaAsset:
    """Media file to upload."""
    path: str
    type: str  # "image", "video"
    alt_text: str = ""
    width: int = 0
    height: int = 0
    duration: float = 0.0  # for video


@dataclass
class PostContent:
    """Content for a post."""
    title: str
    description: str
    tags: List[str] = field(default_factory=list)
    affiliate_link: str = ""
    product_name: str = ""
    price: str = ""
    category: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PostResult:
    """Result of a post attempt."""
    platform: str
    status: PostStatus
    post_id: Optional[str] = None
    post_url: Optional[str] = None
    error: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    metrics: Dict[str, Any] = field(default_factory=dict)  # views, likes, etc.


class Platform(ABC):
    """Base class for all social platforms."""
    
    PLATFORM_NAME: str = "base"
    MAX_TAGS: int = 20
    MAX_TITLE_LENGTH: int = 100
    MAX_DESC_LENGTH: int = 2200
    SUPPORTED_MEDIA: List[str] = ["image"]
    VIDEO_MAX_DURATION: int = 60  # seconds
    VIDEO_MAX_SIZE_MB: int = 100
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.credentials = config.get("credentials", {})
        self.enabled = config.get("enabled", True)
        self.rate_limit = config.get("rate_limit", {})
        self._session = None
    
    @abstractmethod
    async def authenticate(self) -> bool:
        """Authenticate with platform. Return True if successful."""
        pass
    
    @abstractmethod
    async def post(self, content: PostContent, media: List[MediaAsset]) -> PostResult:
        """Post content to platform. Return PostResult."""
        pass
    
    @abstractmethod
    async def get_analytics(self, post_id: str) -> Dict[str, Any]:
        """Get analytics for a post."""
        pass
    
    @abstractmethod
    async def delete_post(self, post_id: str) -> bool:
        """Delete a post."""
        pass
    
    def validate_content(self, content: PostContent) -> List[str]:
        """Validate content before posting. Return list of errors."""
        errors = []
        if len(content.title) > self.MAX_TITLE_LENGTH:
            errors.append(f"Title too long: {len(content.title)}/{self.MAX_TITLE_LENGTH}")
        if len(content.description) > self.MAX_DESC_LENGTH:
            errors.append(f"Description too long: {len(content.description)}/{self.MAX_DESC_LENGTH}")
        if len(content.tags) > self.MAX_TAGS:
            errors.append(f"Too many tags: {len(content.tags)}/{self.MAX_TAGS}")
        return errors
    
    def format_tags(self, tags: List[str]) -> str:
        """Format tags for platform."""
        return " ".join(f"#{tag.lstrip('#')}" for tag in tags[:self.MAX_TAGS])
    
    def is_healthy(self) -> bool:
        """Check if platform is configured and healthy."""
        return self.enabled and bool(self.credentials)
    
    def __repr__(self):
        return f"<{self.PLATFORM_NAME}Platform enabled={self.enabled}>"
