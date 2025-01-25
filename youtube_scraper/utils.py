import re
from typing import Optional, Union, List
from fake_useragent import UserAgent
from datetime import datetime
import aiohttp
import asyncio
from bs4 import BeautifulSoup
import json
import logging
from pathlib import Path
import pandas as pd
from rich.progress import Progress
from rich.console import Console
from rich.logging import RichHandler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[RichHandler(rich_tracebacks=True)]
)
logger = logging.getLogger("youtube_scraper")
console = Console()

def extract_video_id(url: str) -> Optional[str]:
    """Extract video ID from various YouTube URL formats."""
    patterns = [
        r"(?:v=|\/)([0-9A-Za-z_-]{11}).*",
        r"(?:embed\/)([0-9A-Za-z_-]{11})",
        r"(?:shorts\/)([0-9A-Za-z_-]{11})",
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

def extract_channel_id(url: str) -> Optional[str]:
    """Extract channel ID from various YouTube channel URL formats."""
    patterns = [
        r"(?:channel\/)([0-9A-Za-z_-]+)",
        r"(?:c\/)([0-9A-Za-z_-]+)",
        r"(?:user\/)([0-9A-Za-z_-]+)",
        r"(?:@)([0-9A-Za-z_-]+)",
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

async def get_random_proxy() -> Optional[str]:
    """Get a random working proxy from public proxy lists."""
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get("https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=10000&country=all&ssl=all&anonymity=all") as response:
                if response.status == 200:
                    proxies = (await response.text()).strip().split("\n")
                    return f"http://{proxies[0]}" if proxies else None
        except Exception as e:
            logger.warning(f"Failed to fetch proxy: {e}")
    return None

async def make_request(url: str, proxy: Optional[str] = None, retries: int = 3) -> Optional[str]:
    """Make an HTTP request with retry logic and proxy support."""
    headers = {"User-Agent": UserAgent().random}
    
    for attempt in range(retries):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, proxy=proxy, timeout=30) as response:
                    if response.status == 200:
                        return await response.text()
                    elif response.status == 429:
                        wait_time = int(response.headers.get("Retry-After", 60))
                        logger.warning(f"Rate limited. Waiting {wait_time} seconds...")
                        await asyncio.sleep(wait_time)
                    else:
                        logger.warning(f"Request failed with status {response.status}")
        except Exception as e:
            logger.warning(f"Request failed: {e}")
            await asyncio.sleep(2 ** attempt)
    return None

def parse_date(date_str: str) -> datetime:
    """Parse various YouTube date formats into datetime objects."""
    formats = [
        "%Y-%m-%d",
        "%Y%m%d",  # Added format for YYYYMMDD
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%d %H:%M:%S",
        "%b %d, %Y",
        "%Y-%m-%d %H:%M:%S.%f",
    ]
    
    # Convert YYYYMMDD to YYYY-MM-DD
    if len(date_str) == 8 and date_str.isdigit():
        date_str = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
            
    raise ValueError(f"Unable to parse date: {date_str}")

def save_to_file(data: Union[List, dict], filename: str, format: str = "csv"):
    """Save scraped data to file in various formats."""
    # Convert filename to Path object and resolve it
    filepath = Path(filename).resolve()
    
    # Create parent directory if it doesn't exist
    filepath.parent.mkdir(parents=True, exist_ok=True)
    
    # Add extension if not present
    if not filepath.suffix:
        filepath = filepath.with_suffix(f".{format}")
    
    if format == "csv":
        pd.DataFrame(data).to_csv(filepath, index=False)
    elif format == "json":
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)
    elif format == "excel":
        pd.DataFrame(data).to_excel(filepath, index=False)
    else:
        raise ValueError(f"Unsupported format: {format}")
    
    logger.info(f"Data saved to {filepath}")

def format_number(num: Union[int, float]) -> str:
    """Format large numbers in a human-readable way."""
    if num >= 1_000_000:
        return f"{num/1_000_000:.1f}M"
    elif num >= 1_000:
        return f"{num/1_000:.1f}K"
    return str(num)

def create_progress_bar(total: int, description: str) -> Progress:
    """Create a rich progress bar for tracking scraping progress."""
    progress = Progress(
        "[progress.description]{task.description}",
        "[progress.percentage]{task.percentage:>3.0f}%",
        "•",
        "[progress.bar]{task.completed}/{task.total}",
    )
    progress.add_task(description, total=total)
    return progress 