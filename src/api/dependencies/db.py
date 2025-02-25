# src/api/dependencies/db.py
from typing import Union, List
from sqlalchemy import text
from sqlalchemy.engine import Row

from src.schema.video import (
    StudentDeploymentDetails,
    DeploymentPackage,
    DeploymentStep,
    DeploymentComponent,
)
from src.database import get_mysql_db


def select_student_deployment_details(
    deployment_id: int, to_pydantic: bool = True
) -> Union[StudentDeploymentDetails, List[Row]]:
    """
    Fetch student deployment details from the database.

    Args:
        deployment_id (int): The ID of the deployment to fetch details for.
        to_pydantic (bool): If True, returns the results as a Pydantic model. If False, returns raw query results.

    Returns:
        Union[StudentDeploymentDetails, List[Row]]: The query results, either as a Pydantic model or raw rows.
    """
    query: str = """
    SELECT
        s.first_name,
        s.last_name,
        s.email,
        s.tech_experience_id,
        s.employment_status_id,
        c.name AS cohort_name,
        c.start_date AS cohort_start_date,
        c.end_date AS cohort_end_date,
        d.id AS deployment_id,
        d.start_date AS deployment_start_date,
        d.end_date AS deployment_end_date,
        d.acc_grading,
        d.acc_score,
        d.otd_grading,
        d.otd_score,
        d.opt_grading,
        d.opt_score,
        d.func_grading,
        d.func_score,
        ds.grading AS step_grading,
        ds.score AS step_score,
        ds.objectives AS step_objectives,
        ds.instructions AS step_instructions,
        dc.grading AS component_grading,
        dc.score AS component_score,
        dc.deployment_component_id,
        dp.name AS deployment_package_name,
        dp.id AS deployment_package_id,
        CONCAT(dp.objectives, '\n\n', dp.notes) AS deployment_package_description
    FROM
        itp_students s
    JOIN
        itp_cohorts c ON s.cohort_id = c.id
    JOIN
        itp_student_deployments d ON s.id = d.student_id
    LEFT JOIN
        itp_student_deployment_steps ds ON d.id = ds.student_deployment_id
    LEFT JOIN
        itp_student_deployment_components dc ON d.id = dc.student_deployment_id
    LEFT JOIN
        itp_deployment_packages dp ON d.deployment_package_id = dp.id
    WHERE
        d.id = :deployment_id
    """
    db = next(get_mysql_db())
    results: List[Row] = db.execute(
        text(query),
        {
            "deployment_id": deployment_id
        }
    ).fetchall()

    if not to_pydantic:
        return results

    # First row has the common data
    # Did this because the current version of MySQL does't have JSON AGG
    first_row: Row = results[0]

    # Parse components and steps from all rows
    components: List[DeploymentComponent] = []
    steps: List[DeploymentStep] = []
    for row in results:
        if row.component_grading:
            components.append(
                DeploymentComponent(
                    grading=row.component_grading,
                    score=row.component_score,
                    deployment_component_id=row.deployment_component_id,
                )
            )
        if row.step_grading:
            steps.append(
                DeploymentStep(
                    grading=row.step_grading,
                    score=row.step_score,
                    objectives=row.step_objectives,
                    instructions=row.step_instructions,
                )
            )

    deployment_package: DeploymentPackage = DeploymentPackage(
        id=first_row.deployment_package_id,
        name=first_row.deployment_package_name,
        description=first_row.deployment_package_description,
    )

    return StudentDeploymentDetails(
        first_name=first_row.first_name,
        last_name=first_row.last_name,
        email=first_row.email,
        tech_experience_id=first_row.tech_experience_id,
        employment_status_id=first_row.employment_status_id,
        cohort_name=first_row.cohort_name,
        cohort_start_date=first_row.cohort_start_date,
        cohort_end_date=first_row.cohort_end_date,
        deployment_id=first_row.deployment_id,
        deployment_start_date=first_row.deployment_start_date,
        deployment_end_date=first_row.deployment_end_date,
        acc_grading=first_row.acc_grading,
        acc_score=first_row.acc_score,
        otd_grading=first_row.otd_grading,
        otd_score=first_row.otd_score,
        opt_grading=first_row.opt_grading,
        opt_score=first_row.opt_score,
        func_grading=first_row.func_grading,
        func_score=first_row.func_score,
        components=components,
        steps=steps,
        deployment_package=deployment_package,
    )
