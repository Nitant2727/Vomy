# YouTube Scraper CLI

A simple command-line tool for scraping YouTube channel data with proxy rotation and anti-bot detection.

## Features

- Scrape channel information
- Scrape video metadata
- Scrape video comments
- Scrape channel playlists
- Proxy rotation support
- Anti-bot detection mechanisms
- JSON output format
- Interactive mode for customizing scraping options

## Installation

```bash
pip install -e .
```

## Usage

```bash
# Basic usage
youtube-scraper channel https://www.youtube.com/@ChannelName

# With proxy rotation
youtube-scraper channel https://www.youtube.com/@ChannelName --use-proxies

# With custom sleep interval
youtube-scraper channel https://www.youtube.com/@ChannelName --sleep-interval 5.0
```

### Interactive Options

The tool will ask you what data you want to scrape:

1. Basic channel info
2. Videos (with customizable limit)
3. Video details (views, likes, etc.)
4. Comments (with customizable limit)
5. Playlists

### Output

All scraped data is saved in a timestamped directory under `./output/` (or your specified directory) in JSON format.

## Project Structure

```
youtube_scraper/
├── youtube_scraper/
│   ├── __init__.py
│   ├── cli.py           # Command-line interface
│   ├── scraper.py       # Main scraper implementation
│   ├── models.py        # Data models
│   ├── utils.py         # Utility functions
│   ├── config/
│   │   ├── __init__.py
│   │   └── settings.py  # Configuration settings
│   └── data/
│       └── proxies.txt  # Custom proxy list
├── setup.py             # Package setup
├── requirements.txt     # Dependencies
├── README.md           # Documentation
└── LICENSE             # MIT License
```

## Credentials

This tool does not require any API keys or credentials. It works by:

1. Using proxy rotation to avoid rate limiting
2. Implementing browser-like behavior to avoid bot detection
3. Using public proxy lists (automatically fetched)

### Optional: Custom Proxies

You can add your own proxies to `youtube_scraper/data/proxies.txt`:
```
http://your-proxy-ip:port
http://another-proxy-ip:port
```

## Requirements

- Python 3.8 or higher
- Internet connection
- (Optional) Proxy list for proxy rotation

## License

MIT License 