# services/dialogue/script.py
import json

from sqlalchemy.orm import Session

from src.models.video import Script, DeploymentPackageExt, ScriptStatus
from src.schema.itp import ScriptPromptData
from src.services.dialogue.chains import create_script_chain
from src.logging_config import app_logger

from langchain_core.output_parsers.json import parse_json_markdown

# TODO: This needs better handling of constructed prompt.


async def generate(
        script_prompt_data: ScriptPromptData,
        db: Session
) -> Script:
    """Generate script for a deployment"""

    full_prompt = {
        "prompt": script_prompt_data.deployment_details.package.prompt,
        "components_summary": script_prompt_data.components_summary,
        "deployment_details": script_prompt_data.deployment_details,
        "cohort_comparison": script_prompt_data.cohort_comparison
    }

    chain = create_script_chain()
    response = await chain.arun(
        {
            "prompt": full_prompt
        }
    )

    app_logger.debug(f"Response: {response}")

    # Create a new Script object
    # TODO: Check if response is a valid JSON
    # TODO: save complete prompt to the database
    script = Script(
        student_deployment_id=script_prompt_data.deployment_details.deployment.id,
        scene_dialogue=json.dumps(parse_json_markdown(response)),
        prompt_used=script_prompt_data.model_dump_json(),
        status=ScriptStatus.COMPLETE
    )

    # Add the script to the database
    db.add(script)
    db.commit()
    db.refresh(script)

    return script
