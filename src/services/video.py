# src/services/video.py
import logging
from sqlalchemy.orm import Session
from sqlalchemy import text
from ..models.schema import (
    Video,
    VideoStatus,
    ScoreRange,
    ScoreType,
    Template,
    TemplateContent
)
from .synthesia import SynthesiaClient

logger = logging.getLogger(__name__)


class VideoGenerator:
    def __init__(
        self, sqlite_db: Session, mysql_db: Session, synthesia: SynthesiaClient
    ):
        self.sqlite_db = sqlite_db
        self.mysql_db = mysql_db
        self.synthesia = synthesia

    def generate_video(self, student_deployment_id: int):
        video = None
        try:
            # Get deployment data
            data = self._gather_deployment_data(student_deployment_id)

            # Get active template
            template = self._get_active_template(data["workload_number"])
            if not template:
                raise ValueError("No active template found")

            # Create video record
            video = Video(
                student_deployment_id=student_deployment_id, status=VideoStatus.PENDING
            )
            self.sqlite_db.add(video)
            self.sqlite_db.commit()

            # Get content for the overall score
            overall_contents = self._get_content_for_score(
                template.id, data["overall_score"], ScoreType.OVERALL
            )

            # Fetch template variables
            template_variables = self.synthesia.get_template_variables(
                template.synthesia_template_id
            )

            logger.info(f"template vars: {template_variables}")

            breakpoint()

            # Map variables for Synthesia
            variables = self._map_template_variables(
                template, overall_contents, data, template_variables
            )

            # Generate video
            response = self.synthesia.create_video_from_template(
                template_id=template.synthesia_template_id, variables=variables
            )

            # Update video record
            video.synthesia_video_id = response["id"]
            video.status = VideoStatus.PROCESSING
            self.sqlite_db.commit()

            return response["id"]

        except Exception as e:
            logger.error(f"Failed to generate video: {str(e)}")
            if video:
                video.status = VideoStatus.FAILED
                self.sqlite_db.commit()
            raise

    def _get_score_range(self, score: float) -> ScoreRange:
        return (
            self.sqlite_db.query(ScoreRange)
            .filter(ScoreRange.min_score <= score, ScoreRange.max_score >= score)
            .first()
        )

    def _get_template_contents(self, template_id: str, score_range_id: str) -> list:
        return (
            self.sqlite_db.query(TemplateContent)
            .filter(
                TemplateContent.template_id == template_id,
                TemplateContent.score_range_id == score_range_id,
            )
            .all()
        )

    def _map_template_variables(self, template, contents, data, template_variables):
        variables = {}

        # Map static variables
        for synth_var in template_variables:
            if synth_var in data:
                variables[synth_var] = data[synth_var]
            else:
                # Provide a default value for missing variables
                variables[synth_var] = str()

        # Map dynamic content (e.g., score-based content)
        for content in contents:
            if content.variable_name in template_variables:
                variables[content.variable_name] = content.content

        return variables

    def _get_active_template(self, deployment_package_id: int) -> Template:
        return (
            self.sqlite_db.query(Template)
            .filter(Template.deployment_package_id == deployment_package_id)
            .first()
        )

    def _get_content_for_score(self, template_id: str, score: float, score_type: ScoreType) -> list:
        """
        Fetches the template content for the given score and score type.
        """
        # Get the score range for the score
        score_range = self._get_score_range(score)

        # Get the template contents for this range and score type
        template_contents = (
            self.sqlite_db.query(TemplateContent)
            .filter(
                TemplateContent.template_id == template_id,
                TemplateContent.score_range_id == score_range.id,
                TemplateContent.score_type == score_type,
            )
            .all()
        )

        return template_contents

    def _gather_deployment_data(self, deployment_id: int) -> dict:
        """
        Fetches deployment data for a student, including:
        - first_name
        - last_name
        - overall_score
        """
        # Fetch deployment data from MySQL
        deployment = self.mysql_db.execute(
            text(
                """
            SELECT
                d.*,
                s.first_name,
                s.last_name
            FROM itp_student_deployments d
            JOIN itp_students s ON d.student_id = s.id
            WHERE d.id = :deployment_id
            """
            ),
            {"deployment_id": deployment_id},
        ).fetchone()

        if not deployment:
            raise ValueError(f"No deployment found for ID: {deployment_id}")

        # Extract required fields
        data = {
            "first_name": deployment.first_name,
            "last_name": deployment.last_name,
            "overall_score": deployment.acc_score,
            "workload_number": deployment.deployment_package_id,
        }
        logger.info(f"deployment data: {data}")

        return data
