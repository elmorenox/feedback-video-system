# services/dialogue/script.py
import json

from langchain.chains import LLMChain
from sqlalchemy.orm import Session

from src.models.video import Script as ORMScript
from src.schema.video import Script, ScriptRequestPayload, ScriptStatus
from src.services.dialogue.chains import create_script_chain
from src.logging_config import app_logger

from langchain_core.output_parsers.json import parse_json_markdown


async def generate(
        payload: ScriptRequestPayload,
        db: Session
) -> Script:
    """Generate script for a student deployment package"""

    chain: LLMChain = create_script_chain()
    response = await chain.arun(
        {
            "prompt": payload
        }
    )

    # Check to see if there is a script associated with the student deployment.id
    existing_script = db.query(ORMScript).filter(
        ORMScript.student_deployment_id == payload.student_deployment.id
    ).first()

    # If there is an existing script, update it
    if existing_script:
        existing_script.scene_dialogue = json.dumps(
            parse_json_markdown(
                response
            )
        )
        existing_script.prompt_used = payload.model_dump_json()
        existing_script.status = ScriptStatus.COMPLETE
        db.commit()
        db.refresh(existing_script)
        return Script.model_validate(existing_script)

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
