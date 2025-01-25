"""
Configuration settings for the YouTube scraper.
"""

# Proxy settings
PROXY_REFRESH_INTERVAL = 300  # 5 minutes
PROXY_SOURCES = [
    'https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt',
    'https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/http.txt',
    'https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt'
]

# Request settings
DEFAULT_SLEEP_INTERVAL = 3.0
MAX_RETRIES = 3
REQUEST_TIMEOUT = 30

# Browser profiles for anti-bot detection
BROWSER_PROFILES = [
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

# Default headers
DEFAULT_HEADERS = {
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
    'Cache-Control': 'no-cache',
    'Pragma': 'no-cache',
} 