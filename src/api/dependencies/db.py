from typing import Dict, List, Optional, Union
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
        comp.id AS component_id,
        comp.title AS component_title,
        comp.description AS component_description,
        dps.component_name,
        dps.component_category,
        dps.deployment_component_id AS package_component_id,
        dp.name AS deployment_package_name,
        dp.id AS deployment_package_id,
        dp.objectives AS deployment_package_objectives,
        dp.notes AS deployment_package_notes
    FROM
        itp_students s
    JOIN
        itp_cohorts c ON s.cohort_id = c.id
    JOIN
        itp_student_deployments d ON s.id = d.student_id
    LEFT JOIN
        itp_student_deployment_components dc ON d.id = dc.student_deployment_id
    LEFT JOIN
        itp_deployment_components comp ON dc.deployment_component_id = comp.id
    LEFT JOIN
        itp_deployment_package_steps dps ON d.deployment_package_id = dps.deployment_package_id 
            AND dps.deployment_component_id = dc.deployment_component_id
    LEFT JOIN
        itp_student_deployment_steps ds ON d.id = ds.student_deployment_id
            AND ds.deployment_step_id = dps.deployment_step_id
    LEFT JOIN
        itp_deployment_packages dp ON d.deployment_package_id = dp.id
    WHERE
        d.id = :deployment_id
    ORDER BY
        comp.id, ds.id
    """
    db = next(get_mysql_db())
    results: List[Row] = db.execute(
        text(query), {"deployment_id": deployment_id}
    ).fetchall()

    if not to_pydantic:
        return results

    # First row has the common data
    first_row: Row = results[0]

    # Dictionary to track components by ID
    components_by_id = {}

    for row in results:
        if row.component_id is not None:
            # Get or create component
            if row.component_id not in components_by_id:
                component = DeploymentComponent(
                    id=row.component_id,
                    component_category=row.component_title,
                    description=row.component_description,
                    grading=row.component_grading,
                    score=row.component_score,
                    steps=[],
                )
                components_by_id[row.component_id] = component

            # Add step if present
            if row.step_grading:
                step = DeploymentStep(
                    grading=row.step_grading,
                    score=row.step_score,
                    objectives=row.step_objectives,
                    instructions=row.step_instructions,
                    deployment_component_id=row.deployment_component_id,
                    step_name=row.component_name,
                    component_category=row.component_category,
                )
                components_by_id[row.component_id].steps.append(step)

    # Get list of all components
    components = list(components_by_id.values())

    deployment_package: DeploymentPackage = DeploymentPackage(
        id=first_row.deployment_package_id,
        name=first_row.deployment_package_name,
        notes=first_row.deployment_package_notes,
        objectives=first_row.deployment_package_objectives,
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
        deployment_package=deployment_package,
    )


def get_student_info(deployment_id: int) -> Optional[Row]:
    """
    Get basic information about a student's deployment.

    Args:
        deployment_id: The ID of the student's deployment

    Returns:
        Row object with student information or None if not found
    """
    query = """
    SELECT 
        sd.id AS deployment_id,
        sd.student_id,
        sd.deployment_package_id,
        sd.acc_score,
        s.cohort_id,
        c.name AS cohort_name,
        s.first_name,
        s.last_name
    FROM 
        itp_student_deployments sd
    JOIN 
        itp_students s ON sd.student_id = s.id
    JOIN 
        itp_cohorts c ON s.cohort_id = c.id
    WHERE 
        sd.id = :deployment_id
    """

    db = next(get_mysql_db())
    return db.execute(text(query), {"deployment_id": deployment_id}).fetchone()


def get_cohort_scores(cohort_id: int, package_id: int) -> List[Row]:
    """
    Get accuracy scores for all students in a cohort for a specific package.

    Args:
        cohort_id: The cohort ID
        package_id: The deployment package ID

    Returns:
        List of Row objects containing accuracy scores
    """
    query = """
    SELECT 
        sd.acc_score
    FROM 
        itp_student_deployments sd
    JOIN 
        itp_students s ON sd.student_id = s.id
    WHERE 
        s.cohort_id = :cohort_id 
        AND sd.deployment_package_id = :package_id
        AND sd.acc_score IS NOT NULL
    """

    db = next(get_mysql_db())
    return db.execute(
        text(query), {"cohort_id": cohort_id, "package_id": package_id}
    ).fetchall()


def calculate_percentile_metrics(
    student_score: float, cohort_scores: List[Row]
) -> Dict:
    """
    Calculate percentile and related metrics.

    Args:
        student_score: The student's accuracy score
        cohort_scores: List of accuracy scores for the cohort

    Returns:
        Dict with calculated metrics
    """
    total_students = len(cohort_scores)

    if total_students == 0:
        return {
            "total_students": 0,
            "students_below_or_equal": 0,
            "cohort_avg_acc_score": 0,
            "percentile": 0,
            "rank": "N/A",
        }

    students_below_or_equal = sum(
        1 for score in cohort_scores if score.acc_score <= student_score
    )
    cohort_avg_acc_score = (
        sum(score.acc_score for score in cohort_scores) / total_students
    )
    percentile = (students_below_or_equal / total_students) * 100

    rank_ordinal = get_ordinal_suffix(students_below_or_equal)
    rank = f"{students_below_or_equal}{rank_ordinal} out of {total_students}"

    return {
        "total_students": total_students,
        "students_below_or_equal": students_below_or_equal,
        "cohort_avg_acc_score": round(cohort_avg_acc_score, 2),
        "percentile": round(percentile, 1),
        "rank": rank,
    }


def get_ordinal_suffix(n: int) -> str:
    """Return the ordinal suffix for a number."""
    if 11 <= n % 100 <= 13:
        return "th"
    else:
        return {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
