import logging
from src.settings import Settings
from src.models.database import (
    get_sqlite_db,
    get_mysql_db,
    close_ssh_tunnel,
)  # Import both session factories and SSH tunnel closer
from src.services.synthesia import SynthesiaClient
from src.services.video import VideoGenerator
from src.utils.logger import setup_logger

# Initialize logging
setup_logger()
logger = logging.getLogger(__name__)


def main(deployment_id: int = 500):
    # Get SQLite and MySQL database sessions
    sqlite_db = next(get_sqlite_db())
    mysql_db = next(get_mysql_db())

    # Initialize SynthesiaClient
    synthesia = SynthesiaClient()

    try:
        # Initialize VideoGenerator with both database sessions
        generator = VideoGenerator(sqlite_db, mysql_db, synthesia)

        # Generate the video
        video_id = generator.generate_video(deployment_id)
        logger.info(f"Generated video: {video_id}")
        return video_id
    except Exception as e:
        logger.error(f"Failed to generate video: {str(e)}")
        raise
    finally:
        # Close both database sessions
        sqlite_db.close()
        mysql_db.close()
        # Close the SSH tunnel
        close_ssh_tunnel()


if __name__ == "__main__":
    # Example deployment ID, you can pass this as an argument or from a config
    main()
