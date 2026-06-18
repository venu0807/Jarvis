"""
Pinterest Platform Engine
Single-platform focus (post video/images to Pinterest)
"""

from .base import Platform, PostResult, MediaAsset
from .pinterest import PinterestPlatform

__all__ = [
    "Platform",
    "PostResult",
    "MediaAsset",
    "PinterestPlatform",
    "get_platform",
    "PLATFORMS",
]

# Registry — Pinterest-only
PLATFORMS = {
    "pinterest": PinterestPlatform,
}


def get_platform(name: str, config: dict) -> "Platform":
    """Get platform instance by name."""
    if name not in PLATFORMS:
        raise ValueError(f"Unknown platform: {name}. Available: {list(PLATFORMS.keys())}")
    return PLATFORMS[name](config)
