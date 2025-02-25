# services/dialogue/script.py
from sqlalchemy.orm import Session
from sqlalchemy import select
from src.models.video import Script, DeploymentPackageExt, ScriptStatus
from src.schema.video import StudentDeploymentDetails
from src.services.dialogue.chains import create_script_chain
from src.logging_config import app_logger


async def generate(
        grading_data: StudentDeploymentDetails,
        db: Session
) -> Script:
    """Generate script for a deployment"""
    app_logger.debug("Getting prompt template")

    # Access deployment_package directly from grading_data
    deployment_package_id = grading_data.deployment_package.id

    stmt = select(DeploymentPackageExt).where(
        DeploymentPackageExt.deployment_package_id == deployment_package_id
    )
    deployment_package: DeploymentPackageExt = db.execute(stmt).scalar_one()

    app_logger.debug("Creating script chain")
    chain = create_script_chain()
    response = await chain.arun({
        "prompt": deployment_package.prompt_template,
        "grading_data": grading_data.model_dump()
    })

    app_logger.debug(f"Response: {response}")

    # Create a new Script object
    script = Script(
        student_deployment_id=grading_data.deployment_id,
        raw_llm_response=response,
        prompt_used=deployment_package.prompt_template,
        status=ScriptStatus.COMPLETE
    )

    # Add the script to the database
    db.add(script)
    db.commit()
    db.refresh(script)
    return script
