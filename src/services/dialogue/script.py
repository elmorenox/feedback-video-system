# services/dialogue/script.py
from sqlalchemy.orm import Session
from src.models.video import Script, DeploymentPackageExt
from src.services.dialogue.chains import create_script_chain
from src.logging_config import app_logger


async def generate(grading_data: dict, db: Session) -> Script:
    """Generate script for a deployment"""
    # Get prompt template
    app_logger.debug("Getting prompt template")

    prompt_template = db.query(DeploymentPackageExt).filter(
        DeploymentPackageExt.deployment_package_id == grading_data[0][27]
    ).first()

    app_logger.debug("creating script chain")
    # Generate script using LangChain
    chain = create_script_chain()
    response = await chain.arun({
        "prompt": prompt_template.prompt_template,
        "grading_data": grading_data
    })

    app_logger.debug(f"response {response}")

    # Create script record
    script = Script(
        student_deployment_id=500,
        raw_llm_response=response,
        prompt_used=prompt_template.prompt_template,
        status="complete",
    )

    db.add(script)
    db.commit()

    return script
