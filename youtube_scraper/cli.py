import click
import asyncio
import os
import json
from datetime import datetime
from .scraper import YouTubeScraper
from .utils import logger

class DateTimeEncoder(json.JSONEncoder):
    """Custom JSON encoder for datetime objects."""
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

def create_output_structure(base_dir: str) -> dict:
    """Create organized output directory structure."""
    dirs = {
        'channel_info': os.path.join(base_dir, 'channel_info'),
        'videos': os.path.join(base_dir, 'videos'),
        'comments': os.path.join(base_dir, 'comments'),
        'playlists': os.path.join(base_dir, 'playlists'),
        'stats': os.path.join(base_dir, 'stats')
    }
    
    # Create base directory first
    os.makedirs(base_dir, exist_ok=True)
    
    # Create all subdirectories
    for dir_path in dirs.values():
        os.makedirs(dir_path, exist_ok=True)
        logger.info(f"Created directory: {dir_path}")
    
    return dirs

def save_json(data: dict, filepath: str):
    """Save data to JSON file with proper formatting."""
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False, cls=DateTimeEncoder)
            
        logger.info(f"Saved data to {filepath}")
    except Exception as e:
        logger.error(f"Failed to save JSON file {filepath}: {str(e)}")
        raise

def get_output_dir() -> str:
    """Get output directory from user input."""
    default_dir = "./output"
    use_default = click.confirm(
        f"Use default output directory ({default_dir})?",
        default=True
    )
    if use_default:
        return default_dir
    return click.prompt("Enter output directory path", type=str)

def get_channel_options():
    """Get channel scraping options from user."""
    options = {
        'basic_info': True,  # Always get basic channel info
        'videos': False,
        'max_videos': None,
        'playlists': False,
    }
    
    options['videos'] = click.confirm("Scrape channel videos?", default=True)
    if options['videos']:
        options['max_videos'] = click.prompt(
            "How many videos to scrape? (Enter 0 for all)",
            type=int,
            default=10
        )
    
    options['playlists'] = click.confirm("Scrape channel playlists?", default=False)
    return options

def get_video_options():
    """Get video scraping options from user."""
    options = {
        'video_details': True,  # Always get video details
        'comments': False,
        'max_comments': None,
    }
    
    options['comments'] = click.confirm("Include video comments?", default=True)
    if options['comments']:
        options['max_comments'] = click.prompt(
            "How many comments to scrape? (Enter 0 for all)",
            type=int,
            default=100
        )
    
    return options

@click.group()
def cli():
    """YouTube Scraper CLI"""
    pass

@cli.command()
@click.argument("url")
@click.option("--use-proxies", is_flag=True, help="Use proxy rotation")
@click.option("--sleep-interval", default=3.0, help="Sleep interval between requests")
def channel(url: str, use_proxies: bool, sleep_interval: float):
    """Scrape YouTube channel data."""
    try:
        # Create base output directory
        output_dir = get_output_dir()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        run_dir = os.path.join(output_dir, timestamp)
        
        # Create organized folder structure
        dirs = create_output_structure(run_dir)
        
        options = get_channel_options()
        
        async def run_scraper():
            scraper = YouTubeScraper(
                use_proxies=use_proxies,
                sleep_interval=sleep_interval
            )
            
            try:
                # Always scrape basic channel info
                channel_data = await scraper.scrape_channel(url)
                if channel_data:
                    output_file = os.path.join(dirs['channel_info'], "channel_info.json")
                    save_json(channel_data.dict(), output_file)
                    click.echo(f"✓ Saved channel info to {output_file}")
                
                # Scrape videos if requested
                if options['videos']:
                    max_videos = None if options['max_videos'] == 0 else options['max_videos']
                    videos = await scraper.scrape_channel_videos(
                        url,
                        max_videos=max_videos
                    )
                    
                    if videos:
                        videos_file = os.path.join(dirs['videos'], "videos.json")
                        video_data = [v.dict() for v in videos]
                        save_json(video_data, videos_file)
                        click.echo(f"✓ Saved {len(video_data)} videos to {videos_file}")
                
                # Scrape playlists if requested
                if options['playlists']:
                    playlists = await scraper.scrape_playlists(url)
                    if playlists:
                        playlists_file = os.path.join(dirs['playlists'], "playlists.json")
                        playlist_data = [p.dict() for p in playlists]
                        save_json(playlist_data, playlists_file)
                        click.echo(f"✓ Saved {len(playlist_data)} playlists to {playlists_file}")
                
                # Save scraping stats
                stats_file = os.path.join(dirs['stats'], "scraping_stats.json")
                save_json(scraper.get_stats(), stats_file)
                
                # Print statistics
                stats = scraper.get_stats()
                click.echo("\nScraping Statistics\n")
                click.echo(f"{'Metric':<15} {'Value':<15}")
                click.echo("-" * 30)
                for key, value in stats.items():
                    click.echo(f"{key:<15} {str(value):<15}")
                
            finally:
                await scraper.close()
        
        asyncio.run(run_scraper())
        
    except Exception as e:
        logger.error(f"Failed to scrape channel data: {str(e)}")
        raise click.ClickException(str(e))

@cli.command()
@click.argument("url")
@click.option("--use-proxies", is_flag=True, help="Use proxy rotation")
@click.option("--sleep-interval", default=3.0, help="Sleep interval between requests")
def video(url: str, use_proxies: bool, sleep_interval: float):
    """Scrape YouTube video data."""
    try:
        # Create base output directory
        output_dir = get_output_dir()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        run_dir = os.path.join(output_dir, timestamp)
        
        # Create organized folder structure
        dirs = create_output_structure(run_dir)
        
        options = get_video_options()
        
        async def run_scraper():
            scraper = YouTubeScraper(
                use_proxies=use_proxies,
                sleep_interval=sleep_interval
            )
            
            try:
                # Always scrape video details
                video_data = await scraper.scrape_video(url)
                if video_data:
                    # Create separate files for different video metrics
                    video_info = video_data.dict()
                    
                    # Basic info
                    basic_info = {
                        'title': video_info.get('title'),
                        'description': video_info.get('description'),
                        'upload_date': video_info.get('upload_date'),
                        'duration': video_info.get('duration'),
                        'channel': video_info.get('channel'),
                        'channel_id': video_info.get('channel_id')
                    }
                    
                    # Convert any None values to empty strings for better JSON serialization
                    basic_info = {k: v if v is not None else '' for k, v in basic_info.items()}
                    save_json(basic_info, os.path.join(dirs['videos'], "video_info.json"))
                    
                    # Metrics - ensure numeric values are integers
                    metrics = {
                        'views': int(video_info.get('view_count', 0) or 0),
                        'likes': int(video_info.get('like_count', 0) or 0),
                        'comments_count': int(video_info.get('comment_count', 0) or 0)
                    }
                    save_json(metrics, os.path.join(dirs['videos'], "video_metrics.json"))
                    
                    click.echo(f"✓ Saved video details to {dirs['videos']}")
                
                # Scrape comments if requested
                if options['comments']:
                    try:
                        comments = await scraper.scrape_comments(
                            url,
                            max_comments=options['max_comments']
                        )
                        if comments:
                            comments_file = os.path.join(dirs['comments'], "video_comments.json")
                            # Convert comment data and handle None values
                            comment_data = []
                            for comment in comments:
                                comment_dict = comment.dict()
                                # Convert None values to appropriate defaults
                                comment_dict = {
                                    k: (v if v is not None else 
                                        0 if k in ['like_count', 'reply_count'] else '')
                                    for k, v in comment_dict.items()
                                }
                                comment_data.append(comment_dict)
                            save_json(comment_data, comments_file)
                            click.echo(f"✓ Saved {len(comment_data)} comments to {comments_file}")
                    except Exception as e:
                        logger.warning(f"Failed to scrape comments: {str(e)}")
                        click.echo("⚠ Failed to scrape comments, but continuing with other data")
                
                # Save scraping stats
                stats_file = os.path.join(dirs['stats'], "scraping_stats.json")
                save_json(scraper.get_stats(), stats_file)
                
                # Print statistics
                stats = scraper.get_stats()
                click.echo("\nScraping Statistics\n")
                click.echo(f"{'Metric':<15} {'Value':<15}")
                click.echo("-" * 30)
                for key, value in stats.items():
                    click.echo(f"{key:<15} {str(value):<15}")
                
            finally:
                await scraper.close()
        
        asyncio.run(run_scraper())
        
    except Exception as e:
        logger.error(f"Failed to scrape video data: {str(e)}")
        raise click.ClickException(str(e))

def main():
    cli()

if __name__ == "__main__":
    main() 