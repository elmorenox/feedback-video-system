import httpx
from ..settings import Settings
import logging

logger = logging.getLogger(__name__)

class SynthesiaClient:
    def __init__(self):
        self.settings = Settings()
        self.base_url = "https://api.synthesia.io/v2"

    def get_template_variables(self, template_id: str) -> list:
        """
        Fetches the list of variables required by the template using httpx.
        """
        url = f"{self.base_url}/templates/{template_id}"
        headers = {
            "Authorization": self.settings.SYNTHESIA_API_KEY,
            "accept": "application/json",
        }

        with httpx.Client(headers=headers) as client:
            response = client.get(url)
            if response.is_success:
                template_data = response.json()
                return template_data.get("variables", [])
            else:
                logger.error(f"Failed to fetch template variables: {response.text}")
                response.raise_for_status()

    def create_video_from_template(self, template_id: str, variables: dict):
        """
        Creates a video from a template using httpx.
        """
        payload = {
            "templateId": template_id,
            "templateData": variables,
            "test": True,
            "visibility": "private",
        }

        logger.info(f"payload {payload}")

        with httpx.Client(
            headers={
                "Authorization": self.settings.SYNTHESIA_API_KEY,
                "accept": "application/json",
                "content-type": "application/json",
            }
        ) as client:
            response = client.post(f"{self.base_url}/videos/fromTemplate", json=payload)
            if not response.is_success:
                logger.error(f"Synthesia error response: {response.text}")
            response.raise_for_status()
            return response.json()
