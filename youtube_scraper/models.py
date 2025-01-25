from pydantic import BaseModel
from typing import List, Optional, Dict
from datetime import datetime

class VideoMetadata(BaseModel):
    video_id: str
    title: str
    description: Optional[str]
    upload_date: datetime
    view_count: int
    like_count: Optional[int]
    comment_count: Optional[int]
    duration: int
    tags: List[str] = []
    thumbnail_url: str
    channel_id: str
    channel_title: str

class Comment(BaseModel):
    comment_id: str
    text: str
    author: str
    author_channel_id: Optional[str]
    like_count: int
    reply_count: int
    published_at: datetime
    updated_at: Optional[datetime]
    is_reply: bool = False
    parent_id: Optional[str] = None

class ChannelMetadata(BaseModel):
    channel_id: str
    title: str
    description: Optional[str]
    subscriber_count: Optional[int]
    video_count: int
    view_count: int
    joined_date: Optional[datetime]
    country: Optional[str]
    custom_url: Optional[str]
    thumbnail_url: str

class PlaylistMetadata(BaseModel):
    playlist_id: str
    title: str
    description: Optional[str]
    video_count: int
    view_count: Optional[int]
    last_updated: datetime
    channel_id: str

class CommunityPost(BaseModel):
    post_id: str
    text: str
    published_at: datetime
    like_count: Optional[int]
    reply_count: Optional[int]
    attachment_type: Optional[str]
    attachment_url: Optional[str]

class ScrapingStats(BaseModel):
    start_time: datetime
    end_time: Optional[datetime]
    total_items: int
    processed_items: int
    success_count: int
    error_count: int
    rate_limits_hit: int
    total_requests: int 