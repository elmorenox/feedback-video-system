# services/dialogue/script.py
import json

from sqlalchemy.orm import Session
from sqlalchemy import select
from src.models.video import Script, DeploymentPackageExt, ScriptStatus
from src.schema.itp import ScriptPromptData
from src.services.dialogue.chains import create_script_chain
from src.logging_config import app_logger

from langchain_core.output_parsers.json import parse_json_markdown


async def generate(
        script_prompt_data: ScriptPromptData,
        db: Session
) -> Script:
    """Generate script for a deployment"""
    app_logger.debug("Getting prompt template")

    deployment_package_id = script_prompt_data.deployment_details.package.id

    stmt = select(DeploymentPackageExt).where(
        DeploymentPackageExt.deployment_package_id == deployment_package_id
    )
    deployment_package: DeploymentPackageExt = db.execute(stmt).scalar_one()

    app_logger.debug("Creating script chain")
    chain = create_script_chain()
    response = await chain.arun(
        {
            "prompt": deployment_package.prompt_template,
            "components_summary": script_prompt_data.deployment_details.deployment.components_summary,
            "cohort_comparison": script_prompt_data.cohort_comparison,
            "grading_data": script_prompt_data.deployment_details.model_dump(),
        }
    )

    app_logger.debug(f"Response: {response}")

    # Create a new Script object
    # TODO: Check if response is a valid JSON
    # TODO: save complete prompt to the database
    script = Script(
        student_deployment_id=script_prompt_data.deployment_details.deployment.id,
        raw_llm_response=response,
        scene_dialogue=json.dumps(parse_json_markdown(response)),
        prompt_used=deployment_package.prompt_template,
        status=ScriptStatus.COMPLETE
    )

    # Add the script to the database
    db.add(script)
    db.commit()
    db.refresh(script)

    return script
