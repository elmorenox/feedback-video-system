# src/services/video.py
import logging
from sqlalchemy.orm import Session
from sqlalchemy import text
from ..models.schema import (
    GradingData,
    Template,
    Video,
    VideoStatus,
)
from ..schema.grading import GradingDataSchema
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
            # Get grading data and validate with Pydantic
            grading_data: GradingDataSchema = self._gather_grading_data(student_deployment_id)
            logger.info(
                f"Gathered grading data for student deployment: {student_deployment_id}"
            )

            breakpoint()
            # Get template for this deployment
            template = self._get_active_template(grading_data.scores.current)
            if not template:
                raise ValueError("No active template found")

            # Create video record in our db
            video = Video(
                student_deployment_id=student_deployment_id, status=VideoStatus.PENDING
            )
            self.sqlite_db.add(video)
            self.sqlite_db.commit()

            # TODO: Here we'll add LLM integration
            # For now, we'll log the data we'd send to LLM
            logger.info("Would send to LLM:")
            logger.info(grading_data.model_dump_json(indent=2))

            # TODO: Once we have LLM integration:
            # llm_response = self._get_llm_response(grading_data)
            # scene_texts = self._parse_llm_response(llm_response)

            # For now, using dummy scene texts
            scene_texts = {
                "scene_1_text": f"Hi {{first_name}}! Your score is {grading_data.scores.current}",
                "scene_2_text": "This is placeholder text for scene 2",
                # ... other scenes
            }

            # Generate video with Synthesia
            response = self.synthesia.create_video_from_template(
                template_id=template.synthesia_template_id,
                variables={
                    **scene_texts,
                    "first_name": grading_data.student_info.name.split()[0],
                    "last_name": grading_data.student_info.name.split()[1],
                    "overall_score": str(grading_data.scores.current),
                },
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

    def _gather_grading_data(self, deployment_id: int) -> GradingDataSchema:
        """Gathers comprehensive data for LLM prompt"""
        # First get basic deployment data
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

        # Get components data
        components = self.mysql_db.execute(
            text(
                """
            SELECT
                dc.title as name,
                c.score,
                c.grading
            FROM itp_student_deployment_components c
            JOIN itp_deployment_components dc 
                ON c.deployment_component_id = dc.id
            WHERE c.student_deployment_id = :deployment_id
        """
            ),
            {"deployment_id": deployment_id},
        ).fetchall()

        # Log raw data for debugging
        logger.info(f"Deployment data: {deployment}")
        logger.info(f"Components data: {components}")

        # Build and validate with Pydantic
        grading_data = GradingDataSchema(
            student_info={
                "name": f"{deployment.first_name} {deployment.last_name}",
                "career_interest": None,  # Optional field
            },
            scores={
                "current": deployment.acc_score,
                "previous": [],  # We'll add this later
            },
            components=[
                {
                    "name": comp.name,
                    "score": comp.score if hasattr(comp, "score") else None,
                    "grading": comp.grading if hasattr(comp, "grading") else None,
                }
                for comp in components
            ],
            feedback={
                "acc_grading": deployment.acc_grading,
                "acc_data": deployment.acc_data,
            },
        )

        # Store in GradingData
        db_record = GradingData(
            student_deployment_id=deployment_id, raw_data=grading_data.model_dump()
        )
        self.sqlite_db.add(db_record)
        self.sqlite_db.commit()

        logger.info(f"Stored grading data for deployment {deployment_id}")
        return grading_data
