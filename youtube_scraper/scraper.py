import yt_dlp
import asyncio
from typing import List, Optional, Dict, Union, Any
from datetime import datetime
import json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from .models import (
    VideoMetadata,
    Comment,
    ChannelMetadata,
    PlaylistMetadata,
    CommunityPost,
    ScrapingStats,
)
from .utils import (
    extract_video_id,
    extract_channel_id,
    get_random_proxy,
    make_request,
    parse_date,
    save_to_file,
    format_number,
    create_progress_bar,
    logger,
)
import aiohttp
from fake_useragent import UserAgent
import random
import time
import logging
from http.cookiejar import MozillaCookieJar
import tempfile
import os
from bs4 import BeautifulSoup

class YouTubeScraper:
    def __init__(
        self,
        use_proxies: bool = False,
        max_retries: int = 3,
        batch_size: int = 50,
        output_format: str = "csv",
        cookies_from_browser: Optional[str] = None,
        cookies_file: Optional[str] = None,
        use_random_user_agent: bool = True,
        use_proxy_rotation: bool = False,
        sleep_interval: float = 1.0,
        user_agents: Optional[List[str]] = None,
    ):
        self.use_proxies = use_proxies
        self.max_retries = max_retries
        self.batch_size = batch_size
        self.output_format = output_format
        self.use_random_user_agent = use_random_user_agent
        self.use_proxy_rotation = use_proxy_rotation
        self.sleep_interval = sleep_interval
        self.stats = ScrapingStats(
            start_time=datetime.now(),
            end_time=None,
            total_items=0,
            processed_items=0,
            success_count=0,
            error_count=0,
            rate_limits_hit=0,
            total_requests=0,
        )
        
        # Enhanced browser fingerprinting
        self.browser_profiles = [
            {
                "platform": "Windows",
                "browser": "Chrome",
                "viewport": {"width": 1920, "height": 1080},
                "screen": {"width": 1920, "height": 1080},
                "color_depth": 24,
                "pixel_ratio": 1
            },
            {
                "platform": "MacOS",
                "browser": "Safari",
                "viewport": {"width": 1440, "height": 900},
                "screen": {"width": 2560, "height": 1600},
                "color_depth": 30,
                "pixel_ratio": 2
            },
            {
                "platform": "Windows",
                "browser": "Firefox",
                "viewport": {"width": 1366, "height": 768},
                "screen": {"width": 1366, "height": 768},
                "color_depth": 24,
                "pixel_ratio": 1
            }
        ]
        
        try:
            self.ua = UserAgent(verify_ssl=False)
        except Exception:
            self.ua = None
            
        self.user_agents = user_agents or [
            self.ua.random for _ in range(10)
        ] if self.ua else [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0"
        ]
        
        self.cookies_file = cookies_file
        self.session = None
        self.proxy_pool = []
        self.last_proxy_refresh = 0
        self.proxy_refresh_interval = 300  # 5 minutes
        
        self._setup_yt_dlp()
        
    def _setup_yt_dlp(self):
        self.yt_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True
        }
        
        if self.cookies_file:
            self.yt_opts['cookiefile'] = self.cookies_file
            
        # Add custom headers
        profile = random.choice(self.browser_profiles)
        headers = self._generate_headers(profile)
        self.yt_opts['http_headers'] = headers
        
    def _generate_headers(self, profile):
        headers = {
            'User-Agent': random.choice(self.user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Sec-CH-UA': '" Not A;Brand";v="99", "Chromium";v="96"',
            'Sec-CH-UA-Mobile': '?0',
            'Sec-CH-UA-Platform': f'"{profile["platform"]}"',
            'Viewport-Width': str(profile["viewport"]["width"]),
            'DPR': str(profile["pixel_ratio"]),
            'Device-Memory': '8',
            'RTT': str(random.randint(50, 150)),
            'Downlink': str(random.uniform(5, 10)),
            'ECT': '4g',
        }
        return headers
        
    async def _get_proxy(self):
        current_time = time.time()
        if not self.proxy_pool or (current_time - self.last_proxy_refresh) > self.proxy_refresh_interval:
            try:
                async with aiohttp.ClientSession() as session:
                    # Get proxies from multiple sources for redundancy
                    sources = [
                        'https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt',
                        'https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/http.txt',
                        'https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt'
                    ]
                    
                    for source in sources:
                        try:
                            async with session.get(source) as response:
                                if response.status == 200:
                                    text = await response.text()
                                    proxies = [f'http://{proxy.strip()}' for proxy in text.split('\n') if proxy.strip()]
                                    self.proxy_pool.extend(proxies)
                        except Exception as e:
                            logging.warning(f"Failed to fetch proxies from {source}: {str(e)}")
                            
                    self.last_proxy_refresh = current_time
            except Exception as e:
                logging.error(f"Error refreshing proxy pool: {str(e)}")
                
        if not self.proxy_pool:
            return None
            
        return random.choice(self.proxy_pool)
        
    def _handle_rate_limit(self, retry_count):
        """Implement exponential backoff with jitter"""
        if retry_count >= self.max_retries:
            raise Exception("Max retries exceeded")
            
        base_delay = min(300, (2 ** retry_count))  # Cap at 5 minutes
        jitter = random.uniform(0, 0.1 * base_delay)  # 10% jitter
        delay = base_delay + jitter
        
        time.sleep(delay)
        
    async def _create_session(self):
        """Create a new session with proper configuration."""
        if not self.session:
            # Configure client session with compression support
            self.session = aiohttp.ClientSession(
                headers={
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Cache-Control': 'no-cache',
                    'Pragma': 'no-cache',
                    'Sec-Ch-Ua': '"Not A(Brand";v="99", "Google Chrome";v="121", "Chromium";v="121"',
                    'Sec-Ch-Ua-Mobile': '?0',
                    'Sec-Ch-Ua-Platform': '"Windows"',
                    'Sec-Fetch-Dest': 'document',
                    'Sec-Fetch-Mode': 'navigate',
                    'Sec-Fetch-Site': 'none',
                    'Sec-Fetch-User': '?1',
                    'Upgrade-Insecure-Requests': '1',
                    'User-Agent': random.choice(self.user_agents)
                }
            )
            
        # Visit trending page first to appear more natural
        try:
            profile = random.choice(self.browser_profiles)
            headers = self._generate_headers(profile)
            async with self.session.get(
                'https://www.youtube.com/feed/trending',
                headers=headers,
                allow_redirects=True,
                timeout=30
            ) as response:
                await response.read()
                await asyncio.sleep(random.uniform(1, 3))
        except Exception as e:
            logging.warning(f"Failed to visit trending page: {str(e)}")
            
    async def _make_request(self, url, retry_count=0):
        if not self.session:
            await self._create_session()
            
        try:
            profile = random.choice(self.browser_profiles)
            headers = self._generate_headers(profile)
            
            proxy = await self._get_proxy() if self.use_proxies else None
            
            async with self.session.get(url, headers=headers, proxy=proxy) as response:
                if response.status == 429:  # Rate limit
                    self._handle_rate_limit(retry_count)
                    return await self._make_request(url, retry_count + 1)
                    
                if response.status == 403:  # Bot detection
                    if proxy:
                        self.proxy_pool.remove(proxy)
                    return await self._make_request(url, retry_count + 1)
                    
                return await response.json()
                
        except Exception as e:
            if retry_count < self.max_retries:
                await asyncio.sleep(random.uniform(self.sleep_interval, self.sleep_interval * 2))
                return await self._make_request(url, retry_count + 1)
            raise e
            
    async def scrape_video(self, url: str) -> Optional[VideoMetadata]:
        """Scrape metadata from a YouTube video with improved error handling."""
        video_id = extract_video_id(url)
        if not video_id:
            logger.error(f"Invalid video URL: {url}")
            return None

        try:
            self.stats.total_requests += 1
            info = await self._make_request(url)
            if not info:
                return None
                
            video = VideoMetadata(
                video_id=video_id,
                title=info["title"],
                description=info.get("description"),
                upload_date=parse_date(info["upload_date"]),
                view_count=info["view_count"],
                like_count=info.get("like_count"),
                comment_count=info.get("comment_count"),
                duration=info["duration"],
                tags=info.get("tags", []),
                thumbnail_url=info["thumbnail"],
                channel_id=info["channel_id"],
                channel_title=info["channel"],
            )
            self.stats.success_count += 1
            return video
        except Exception as e:
            logger.error(f"Failed to scrape video {url}: {e}")
            self.stats.error_count += 1
            return None

    async def scrape_comments(
        self,
        url: str,
        max_comments: Optional[int] = None,
        include_replies: bool = True,
    ) -> List[Comment]:
        """Scrape comments from a YouTube video."""
        video_id = extract_video_id(url)
        if not video_id:
            logger.error(f"Invalid video URL: {url}")
            return []

        comments = []
        try:
            self.stats.total_requests += 1
            with yt_dlp.YoutubeDL(self.yt_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                if "comments" not in info:
                    logger.warning(f"No comments found for video {url}")
                    return []

                for comment_data in info["comments"][:max_comments]:
                    comment = Comment(
                        comment_id=comment_data["id"],
                        text=comment_data["text"],
                        author=comment_data["author"],
                        author_channel_id=comment_data.get("author_id"),
                        like_count=comment_data.get("like_count", 0),
                        reply_count=comment_data.get("reply_count", 0),
                        published_at=parse_date(comment_data["timestamp"]),
                        updated_at=None,
                        is_reply=False,
                    )
                    comments.append(comment)

                    if include_replies and comment_data.get("replies"):
                        for reply in comment_data["replies"]:
                            reply_comment = Comment(
                                comment_id=reply["id"],
                                text=reply["text"],
                                author=reply["author"],
                                author_channel_id=reply.get("author_id"),
                                like_count=reply.get("like_count", 0),
                                reply_count=0,
                                published_at=parse_date(reply["timestamp"]),
                                updated_at=None,
                                is_reply=True,
                                parent_id=comment.comment_id,
                            )
                            comments.append(reply_comment)

                self.stats.success_count += 1
                return comments
        except Exception as e:
            logger.error(f"Failed to scrape comments for video {url}: {e}")
            self.stats.error_count += 1
            return []

    def _handle_cookie_error(self, error: Exception) -> None:
        """Handle cookie-related errors with more helpful messages."""
        if "Could not copy Chrome cookie database" in str(error):
            raise Exception(
                "Could not access Chrome cookies. This can happen if Chrome is running or the cookie database is locked.\n"
                "Please try one of these solutions:\n"
                "1. Close Chrome completely and try again\n"
                "2. Install the 'Get cookies.txt' extension and export cookies to a file\n"
                "3. Use --cookies-file option with the exported cookies file\n"
                "4. Try a different browser with --cookies-from-browser (firefox/opera/edge/safari)"
            )
        elif "could not find firefox cookies" in str(error):
            raise Exception(
                "Could not find Firefox cookies. This can happen if Firefox is not installed or the profile path is different.\n"
                "Please try one of these solutions:\n"
                "1. Make sure Firefox is installed and you've logged into YouTube\n"
                "2. Install the 'Get cookies.txt' extension and export cookies to a file\n"
                "3. Use --cookies-file option with the exported cookies file\n"
                "4. Try a different browser with --cookies-from-browser (chrome/opera/edge/safari)"
            )
        else:
            raise Exception(
                f"Cookie error: {str(error)}\n"
                "Please try one of these solutions:\n"
                "1. Install the 'Get cookies.txt' extension and export cookies to a file\n"
                "2. Use --cookies-file option with the exported cookies file\n"
                "3. Try a different browser with --cookies-from-browser"
            )

    async def scrape_channel(self, url: str, data_type: str = "all") -> Dict[str, Any]:
        """Scrape channel data with improved error handling."""
        try:
            self.stats.total_requests += 1
            
            # Initialize session if needed
            if not self.session:
                await self._create_session()
            
            # Extract channel identifier
            channel_id = url.split("@")[-1] if "@" in url else url.split("/")[-1]
            
            # Try different URL formats
            urls_to_try = [
                f"https://www.youtube.com/@{channel_id}",
                f"https://www.youtube.com/c/{channel_id}",
                f"https://www.youtube.com/channel/{channel_id}"
            ]
            
            html_content = None
            used_url = None
            
            for try_url in urls_to_try:
                try:
                    profile = random.choice(self.browser_profiles)
                    headers = {
                        **self._generate_headers(profile),
                        'Accept-Encoding': 'gzip, deflate, br',
                        'Accept-Language': 'en-US,en;q=0.9',
                        'Cache-Control': 'no-cache',
                        'Pragma': 'no-cache',
                    }
                    
                    proxy = await self._get_proxy() if self.use_proxies else None
                    
                    async with self.session.get(
                        try_url,
                        headers=headers,
                        proxy=proxy,
                        allow_redirects=True,
                        timeout=30
                    ) as response:
                        if response.status == 200:
                            html_content = await response.text()
                            used_url = try_url
                            break
                        elif response.status == 429:  # Rate limit
                            self._handle_rate_limit(0)
                            continue
                        elif response.status == 403:  # Bot detection
                            if proxy:
                                self.proxy_pool.remove(proxy)
                            continue
                        await asyncio.sleep(random.uniform(2, 4))
                except Exception as e:
                    logger.warning(f"Failed to fetch {try_url}: {e}")
                    await asyncio.sleep(random.uniform(1, 2))
                    continue
            
            if not html_content:
                raise Exception("Failed to fetch channel data from all URL formats")
            
            # Extract channel info from HTML
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Extract available metadata
            title = soup.find('meta', property='og:title')
            description = soup.find('meta', property='og:description')
            thumbnail = soup.find('meta', property='og:image')
            
            # Extract subscriber count from script tags
            subscriber_count = 0
            view_count = 0
            video_count = 0
            
            for script in soup.find_all('script'):
                script_text = script.string or ""
                if "subscriberCountText" in script_text:
                    import re
                    # Try to extract subscriber count
                    sub_match = re.search(r'"subscriberCountText":\s*{\s*"simpleText":\s*"([^"]+)"', script_text)
                    if sub_match:
                        sub_text = sub_match.group(1)
                        # Convert text like "1.23M" to number
                        multiplier = {'K': 1000, 'M': 1000000, 'B': 1000000000}.get(sub_text[-1], 1)
                        try:
                            subscriber_count = int(float(sub_text[:-1]) * multiplier)
                        except:
                            pass
                
                if "viewCountText" in script_text:
                    # Try to extract view count
                    view_match = re.search(r'"viewCountText":\s*{\s*"simpleText":\s*"([^"]+)"', script_text)
                    if view_match:
                        view_text = view_match.group(1)
                        try:
                            view_count = int(''.join(filter(str.isdigit, view_text)))
                        except:
                            pass
                
                if "videoCountText" in script_text:
                    # Try to extract video count
                    video_match = re.search(r'"videoCountText":\s*{\s*"runs":\s*\[{\s*"text":\s*"([^"]+)"', script_text)
                    if video_match:
                        video_text = video_match.group(1)
                        try:
                            video_count = int(''.join(filter(str.isdigit, video_text)))
                        except:
                            pass
            
            channel = ChannelMetadata(
                channel_id=channel_id,
                title=title.get('content', channel_id) if title else channel_id,
                description=description.get('content', "") if description else "",
                subscriber_count=subscriber_count,
                video_count=video_count,
                view_count=view_count,
                joined_date=None,
                country="",
                custom_url=used_url or url,
                thumbnail_url=thumbnail.get('content', "") if thumbnail else "",
            )
            
            self.stats.success_count += 1
            return channel
            
        except Exception as e:
            logger.error(f"Failed to scrape channel {url}: {e}")
            self.stats.error_count += 1
            
            # Return partial data if available
            return ChannelMetadata(
                channel_id=channel_id,
                title=channel_id,
                description="",
                subscriber_count=0,
                video_count=0,
                view_count=0,
                joined_date=None,
                country="",
                custom_url=url,
                thumbnail_url="",
            )

    async def scrape_channel_videos(
        self,
        url: str,
        max_videos: Optional[int] = None,
    ) -> List[VideoMetadata]:
        """Scrape all videos from a YouTube channel."""
        try:
            self.stats.total_requests += 1
            with yt_dlp.YoutubeDL({**self.yt_opts, "extract_flat": "in_playlist"}) as ydl:
                info = ydl.extract_info(f"{url}/videos", download=False)
                
                if "entries" not in info:
                    logger.warning(f"No videos found for channel {url}")
                    return []

                entries = info["entries"][:max_videos] if max_videos else info["entries"]
                videos = []
                
                with create_progress_bar(len(entries), "Scraping videos") as progress:
                    for entry in entries:
                        try:
                            # Get full video info for accurate data
                            video_info = ydl.extract_info(
                                f"https://www.youtube.com/watch?v={entry['id']}", 
                                download=False
                            )
                            
                            video = VideoMetadata(
                                video_id=entry["id"],
                                title=entry["title"],
                                description=video_info.get("description", ""),
                                upload_date=parse_date(video_info.get("upload_date", "20000101")),
                                view_count=video_info.get("view_count", 0),
                                like_count=video_info.get("like_count"),
                                comment_count=video_info.get("comment_count"),
                                duration=video_info.get("duration", 0),
                                tags=video_info.get("tags", []),
                                thumbnail_url=video_info.get("thumbnail", ""),
                                channel_id=video_info.get("channel_id", ""),
                                channel_title=video_info.get("channel", ""),
                            )
                            videos.append(video)
                            progress.advance(0)
                        except Exception as e:
                            logger.error(f"Failed to process video {entry.get('id')}: {e}")
                            continue

                self.stats.success_count += 1
                return videos
        except Exception as e:
            logger.error(f"Failed to scrape videos for channel {url}: {e}")
            self.stats.error_count += 1
            return []

    async def scrape_playlists(self, url: str) -> List[PlaylistMetadata]:
        """Scrape all playlists from a YouTube channel."""
        try:
            self.stats.total_requests += 1
            # Try different playlist URLs
            playlist_urls = [
                f"{url}/playlists",
                url.rstrip("/") + "/playlists",
                f"https://www.youtube.com/channel/{extract_channel_id(url)}/playlists" if extract_channel_id(url) else None
            ]
            
            playlists = []
            for playlist_url in playlist_urls:
                if not playlist_url:
                    continue
                    
                try:
                    with yt_dlp.YoutubeDL({**self.yt_opts, "extract_flat": "in_playlist"}) as ydl:
                        info = ydl.extract_info(playlist_url, download=False)
                        
                        if info and "entries" in info:
                            for entry in info["entries"]:
                                try:
                                    playlist = PlaylistMetadata(
                                        playlist_id=entry["id"],
                                        title=entry["title"],
                                        description=entry.get("description", ""),
                                        video_count=entry.get("video_count", 0),
                                        view_count=entry.get("view_count", 0),
                                        last_updated=datetime.now(),  # Use current time as fallback
                                        channel_id=entry.get("channel_id", ""),
                                    )
                                    playlists.append(playlist)
                                except Exception as e:
                                    logger.error(f"Failed to process playlist {entry.get('id')}: {e}")
                                    continue
                            
                            # If we found playlists, no need to try other URLs
                            if playlists:
                                break
                except Exception:
                    continue

            if playlists:
                self.stats.success_count += 1
            else:
                logger.warning(f"No playlists found for channel {url}")
            
            return playlists
        except Exception as e:
            logger.error(f"Failed to scrape playlists for channel {url}: {e}")
            self.stats.error_count += 1
            return []

    async def scrape_community_posts(self, url: str) -> List[CommunityPost]:
        """Scrape community posts from a YouTube channel."""
        channel_id = extract_channel_id(url)
        if not channel_id:
            logger.error(f"Invalid channel URL: {url}")
            return []

        posts = []
        try:
            self.stats.total_requests += 1
            # Community posts require additional parsing as yt-dlp doesn't support them directly
            html = await make_request(f"{url}/community")
            if not html:
                return []

            # Parse community posts from HTML
            # This is a simplified version and might need updates as YouTube's structure changes
            soup = BeautifulSoup(html, "html.parser")
            post_elements = soup.find_all("ytd-backstage-post-thread-renderer")

            for element in post_elements:
                post = CommunityPost(
                    post_id=element.get("id", ""),
                    text=element.find("yt-formatted-string", {"id": "content-text"}).text,
                    published_at=parse_date(element.find("yt-formatted-string", {"id": "published-time-text"}).text),
                    like_count=None,  # These would need additional JavaScript rendering
                    reply_count=None,
                    attachment_type=None,
                    attachment_url=None,
                )
                posts.append(post)

            self.stats.success_count += 1
            return posts
        except Exception as e:
            logger.error(f"Failed to scrape community posts for channel {url}: {e}")
            self.stats.error_count += 1
            return []

    def save_results(
        self,
        data: Union[List, Dict],
        filename: str,
        format: Optional[str] = None,
    ) -> None:
        """Save scraped data to file."""
        save_to_file(data, filename, format or self.output_format)

    def get_stats(self) -> Dict:
        """Get current scraping statistics."""
        self.stats.end_time = datetime.now()
        return self.stats.dict()

    async def close(self):
        """Cleanup resources."""
        if self.session:
            await self.session.close()
            self.session = None
        # Implement cleanup if needed
        pass 