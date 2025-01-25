import click
import asyncio
import os
from datetime import datetime
from .scraper import YouTubeScraper
from .utils import logger

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

def get_scraping_options():
    """Get scraping options from user."""
    options = {
        'basic_info': click.confirm("Scrape basic channel info?", default=True),
        'videos': False,
        'max_videos': None,
        'video_details': False,
        'comments': False,
        'max_comments': None,
        'playlists': False,
    }
    
    if click.confirm("Scrape channel videos?", default=True):
        options['videos'] = True
        options['max_videos'] = click.prompt(
            "How many videos to scrape? (Enter 0 for all)",
            type=int,
            default=10
        )
        if options['max_videos'] > 0:
            options['video_details'] = click.confirm(
                "Include detailed video information (views, likes, etc.)?",
                default=True
            )
            options['comments'] = click.confirm(
                "Include video comments?",
                default=False
            )
            if options['comments']:
                options['max_comments'] = click.prompt(
                    "How many comments per video? (Enter 0 for all)",
                    type=int,
                    default=100
                )
    
    options['playlists'] = click.confirm("Scrape channel playlists?", default=False)
    
    return options

@click.group()
def cli():
    """YouTube Scraper CLI"""
    pass

@cli.command()
@click.argument("url")
@click.option("--use-proxies", is_flag=True, help="Use proxy rotation")
@click.option("--sleep-interval", default=3.0, help="Sleep interval between requests")
@click.option("--format", "output_format", default="json", type=click.Choice(["json", "csv"]))
def channel(url: str, use_proxies: bool, sleep_interval: float, output_format: str):
    """Scrape YouTube channel data."""
    try:
        # Get output directory
        output_dir = get_output_dir()
        os.makedirs(output_dir, exist_ok=True)
        
        # Get scraping options from user
        options = get_scraping_options()
        
        # Create timestamped directory for this run
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        run_dir = os.path.join(output_dir, timestamp)
        os.makedirs(run_dir, exist_ok=True)
        
        async def run_scraper():
            scraper = YouTubeScraper(
                use_proxies=use_proxies,
                sleep_interval=sleep_interval,
                output_format=output_format,
            )
            
            try:
                # Scrape basic channel info if requested
                if options['basic_info']:
                    channel_data = await scraper.scrape_channel(url)
                    if channel_data:
                        output_file = os.path.join(run_dir, "channel_data.json")
                        scraper.save_results(channel_data.dict(), output_file)
                
                # Scrape videos if requested
                if options['videos']:
                    max_videos = None if options['max_videos'] == 0 else options['max_videos']
                    videos = await scraper.scrape_channel_videos(
                        url,
                        max_videos=max_videos
                    )
                    
                    if videos:
                        # Save video metadata
                        videos_file = os.path.join(run_dir, "videos.json")
                        video_data = [v.dict() for v in videos]
                        scraper.save_results(video_data, videos_file)
                        
                        # Scrape comments if requested
                        if options['comments'] and options['max_comments'] >= 0:
                            all_comments = []
                            for video in videos:
                                video_comments = await scraper.scrape_comments(
                                    f"https://www.youtube.com/watch?v={video.video_id}",
                                    max_comments=options['max_comments']
                                )
                                if video_comments:
                                    all_comments.extend([c.dict() for c in video_comments])
                            
                            if all_comments:
                                comments_file = os.path.join(run_dir, "comments.json")
                                scraper.save_results(all_comments, comments_file)
                
                # Scrape playlists if requested
                if options['playlists']:
                    playlists = await scraper.scrape_playlists(url)
                    if playlists:
                        playlists_file = os.path.join(run_dir, "playlists.json")
                        playlist_data = [p.dict() for p in playlists]
                        scraper.save_results(playlist_data, playlists_file)
                
                # Save scraping stats
                stats_file = os.path.join(run_dir, "stats.json")
                scraper.save_results(scraper.get_stats(), stats_file)
                
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
        logger.error(f"Failed to scrape channel data: {e}")
        raise click.ClickException(str(e))

if __name__ == "__main__":
    cli() 