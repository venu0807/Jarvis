"""
Pinterest Platform Implementation
Wraps existing poster.py for API v5 + browser fallback.
"""

import asyncio
import os
import subprocess
import tempfile
import json
from typing import List, Optional, Dict, Any
from datetime import datetime

from .base import Platform, PostContent, MediaAsset, PostResult, PostStatus


class PinterestPlatform(Platform):
    PLATFORM_NAME = "pinterest"
    MAX_TAGS = 20
    MAX_TITLE_LENGTH = 100
    MAX_DESC_LENGTH = 500
    SUPPORTED_MEDIA = ["image", "video"]
    VIDEO_MAX_DURATION = 15 * 60  # 15 minutes
    VIDEO_MAX_SIZE_MB = 2000
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.access_token = self.credentials.get("access_token")
        self.board_id = self.credentials.get("board_id")
        self.use_api = bool(self.access_token and self.board_id)
        self.python_exe = config.get("python_exe", "python")
        self.work_dir = config.get("work_dir", ".")
    
    async def authenticate(self) -> bool:
        """Test API credentials or browser login."""
        if self.use_api:
            # Test API token with a simple request
            try:
                import aiohttp
                headers = {"Authorization": f"Bearer {self.access_token}"}
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        "https://api.pinterest.com/v5/user_account",
                        headers=headers,
                        timeout=10
                    ) as resp:
                        return resp.status == 200
            except Exception:
                return False
        # Browser mode - check if we can launch browser
        return True
    
    async def post(self, content: PostContent, media: List[MediaAsset]) -> PostResult:
        """Post via API v5 or browser fallback."""
        errors = self.validate_content(content)
        if errors:
            return PostResult(
                platform=self.PLATFORM_NAME,
                status=PostStatus.FAILED,
                error="; ".join(errors)
            )
        
        if not media:
            return PostResult(
                platform=self.PLATFORM_NAME,
                status=PostStatus.FAILED,
                error="No media provided"
            )
        
        # Prepare media
        media_path = media[0].path
        if not os.path.exists(media_path):
            return PostResult(
                platform=self.PLATFORM_NAME,
                status=PostStatus.FAILED,
                error=f"Media not found: {media_path}"
            )
        
        if self.use_api:
            return await self._post_api(content, media_path)
        else:
            return await self._post_browser(content, media_path)
    
    async def _post_api(self, content: PostContent, media_path: str) -> PostResult:
        """Post via Pinterest API v5."""
        try:
            import aiohttp
            
            # Upload media first
            upload_url = "https://api.pinterest.com/v5/media"
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }
            
            media_type = "video" if media_path.endswith((".mp4", ".mov")) else "image"
            
            async with aiohttp.ClientSession() as session:
                # Create media
                async with session.post(
                    upload_url,
                    headers=headers,
                    json={"media_type": media_type},
                    timeout=30
                ) as media_resp:
                    if media_resp.status != 201:
                        error_text = await media_resp.text()
                        return PostResult(
                            platform=self.PLATFORM_NAME,
                            status=PostStatus.FAILED,
                            error=f"Media upload failed: {error_text}"
                        )
                    media_data = await media_resp.json()

                media_id = media_data["media_id"]
                upload_url = media_data["upload_url"]

                # Upload file to signed URL
                with open(media_path, "rb") as f:
                    async with session.put(
                        upload_url,
                        data=f,
                        headers={"Content-Type": "application/octet-stream"},
                        timeout=60
                    ) as upload_resp:
                        if upload_resp.status not in (200, 201):
                            error_text = await upload_resp.text()
                            return PostResult(
                                platform=self.PLATFORM_NAME,
                                status=PostStatus.FAILED,
                                error=f"File upload failed: {error_text}"
                            )

                # Create pin
                pin_data = {
                    "board_id": self.board_id,
                    "media_id": media_id,
                    "title": content.title[:self.MAX_TITLE_LENGTH],
                    "description": content.description[:self.MAX_DESC_LENGTH],
                    "link": content.affiliate_link or "",
                    "tags": content.tags[:self.MAX_TAGS]
                }

                async with session.post(
                    "https://api.pinterest.com/v5/pins",
                    headers=headers,
                    json=pin_data,
                    timeout=30
                ) as pin_resp:
                    if pin_resp.status == 201:
                        pin = await pin_resp.json()
                        return PostResult(
                            platform=self.PLATFORM_NAME,
                            status=PostStatus.SUCCESS,
                            post_id=pin.get("id"),
                            post_url=f"https://pinterest.com/pin/{pin.get('id')}",
                            metrics={"method": "api"}
                        )
                    else:
                        error_text = await pin_resp.text()
                        return PostResult(
                            platform=self.PLATFORM_NAME,
                            status=PostStatus.FAILED,
                            error=f"Pin creation failed: {error_text}"
                        )
                
        except Exception as e:
            return PostResult(
                platform=self.PLATFORM_NAME,
                status=PostStatus.FAILED,
                error=f"API error: {str(e)}"
            )
    
    async def _post_browser(self, content: PostContent, media_path: str) -> PostResult:
        """Post via browser automation (existing poster.py)."""
        try:
            # Build command for existing poster
            cmd = [
                self.python_exe, "-m", "poster",
                "--image", media_path,
                "--title", content.title,
                "--description", content.description,
                "--link", content.affiliate_link or "",
                "--tags", ",".join(content.tags),
                "--board", self.credentials.get("browser_board_url", "")
            ]
            
            # Run in background
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=self.work_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=300)
            
            if proc.returncode == 0:
                # Parse output for pin URL
                output = stdout.decode()
                post_id = None
                post_url = None
                
                for line in output.split("\n"):
                    if "pin/" in line and "pinterest.com" in line:
                        post_url = line.strip()
                        post_id = post_url.split("/")[-2] if post_url else None
                        break
                
                return PostResult(
                    platform=self.PLATFORM_NAME,
                    status=PostStatus.SUCCESS,
                    post_id=post_id,
                    post_url=post_url,
                    metrics={"method": "browser", "output": output[-500:]}
                )
            else:
                error = stderr.decode()[-1000:]
                return PostResult(
                    platform=self.PLATFORM_NAME,
                    status=PostStatus.FAILED,
                    error=error
                )
                
        except asyncio.TimeoutError:
            return PostResult(
                platform=self.PLATFORM_NAME,
                status=PostStatus.FAILED,
                error="Browser posting timeout"
            )
        except Exception as e:
            return PostResult(
                platform=self.PLATFORM_NAME,
                status=PostStatus.FAILED,
                error=f"Browser error: {str(e)}"
            )
    
    async def get_analytics(self, post_id: str) -> Dict[str, Any]:
        """Get pin analytics."""
        if not self.use_api:
            return {"error": "Analytics only available via API"}
        
        try:
            import aiohttp
            headers = {"Authorization": f"Bearer {self.access_token}"}
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"https://api.pinterest.com/v5/pins/{post_id}/analytics",
                    headers=headers,
                    params={"metrics": "IMPRESSION,SAVE,CLICKTHROUGH,ENGAGEMENT"},
                    timeout=10
                ) as resp:
                    if resp.status == 200:
                        return await resp.json()
                    return {"error": await resp.text()}
        except Exception as e:
            return {"error": str(e)}
    
    async def delete_post(self, post_id: str) -> bool:
        """Delete a pin."""
        if not self.use_api:
            return False
        
        try:
            import aiohttp
            headers = {"Authorization": f"Bearer {self.access_token}"}
            async with aiohttp.ClientSession() as session:
                async with session.delete(
                    f"https://api.pinterest.com/v5/pins/{post_id}",
                    headers=headers,
                    timeout=10
                ) as resp:
                    return resp.status == 204
        except Exception:
            return False
