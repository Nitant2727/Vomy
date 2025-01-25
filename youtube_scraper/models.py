from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime

class VideoMetadata(BaseModel):
    """Video metadata model."""
    video_id: str
    title: str = ''
    description: str = ''
    upload_date: Optional[str] = ''  # Can be string or datetime
    duration: Optional[int] = 0
    view_count: Optional[int] = 0
    like_count: Optional[int] = 0
    comment_count: Optional[int] = 0
    channel: str = ''
    channel_id: str = ''
    tags: List[str] = Field(default_factory=list)
    categories: List[str] = Field(default_factory=list)

    def __init__(self, **data):
        # Convert datetime to string if needed
        if 'upload_date' in data and isinstance(data['upload_date'], datetime):
            data['upload_date'] = data['upload_date'].strftime('%Y%m%d')
        super().__init__(**data)

class Comment(BaseModel):
    """Comment model."""
    comment_id: str = ''
    text: str = ''
    author: str = ''
    author_id: str = ''
    like_count: int = 0
    reply_count: int = 0
    time: str = ''

class ChannelMetadata(BaseModel):
    """Channel metadata model."""
    channel_id: str
    title: str = ''
    description: str = ''
    subscriber_count: int = 0
    video_count: int = 0
    view_count: int = 0
    joined_date: Optional[str] = ''
    country: str = ''
    custom_url: str = ''
    thumbnail_url: str = ''

class PlaylistMetadata(BaseModel):
    """Playlist metadata model."""
    playlist_id: str
    title: str = ''
    description: str = ''
    video_count: int = 0
    view_count: int = 0
    channel_id: str = ''

class CommunityPost(BaseModel):
    post_id: str
    text: str
    published_at: datetime
    like_count: Optional[int]
    reply_count: Optional[int]
    attachment_type: Optional[str]
    attachment_url: Optional[str]

class ScrapingStats(BaseModel):
    """Scraping statistics model."""
    start_time: str = ''  # ISO format timestamp
    end_time: Optional[str] = None  # ISO format timestamp
    total_items: int = 0
    processed_items: int = 0
    success_count: int = 0
    error_count: int = 0
    rate_limits_hit: int = 0
    total_requests: int = 0

    def __init__(self, **data):
        # Convert datetime objects to ISO format strings
        if 'start_time' in data and isinstance(data['start_time'], datetime):
            data['start_time'] = data['start_time'].isoformat()
        if 'end_time' in data and isinstance(data['end_time'], datetime):
            data['end_time'] = data['end_time'].isoformat()
        super().__init__(**data)

    def update_start_time(self):
        """Update start time with current timestamp."""
        self.start_time = datetime.now().isoformat()
    
    def update_end_time(self):
        """Update end time with current timestamp."""
        self.end_time = datetime.now().isoformat() 