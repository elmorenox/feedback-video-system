# services/dialogue/script.py
import json

from sqlalchemy.orm import Session

from src.models.video import Script as ORMScript
from src.schema.video import Script, ScriptRequestPayload, ScriptStatus
from src.services.dialogue.chains import create_script_chain
from src.logging_config import app_logger

from langchain_core.output_parsers.json import parse_json_markdown

# TODO: This needs better handling of constructed prompt.


async def generate(
        payload: ScriptRequestPayload,
        db: Session
) -> Script:
    """Generate script for a student deployment package"""

    chain = create_script_chain()
    response = await chain.arun(
        {
            "prompt": payload
        }
    )

    # Create a new Script object
    # TODO: Check if response is a valid JSON
    # TODO: save complete prompt to the database
    script = ORMScript(
        student_deployment_id=payload.student_deployment.id,
        scene_dialogue=json.dumps(parse_json_markdown(response)),
        prompt_used=payload.model_dump_json(),
        status=ScriptStatus.COMPLETE
    )

    # Add the script to the database
    db.add(script)
    db.commit()
    db.refresh(script)

    return Script.model_validate(script)
