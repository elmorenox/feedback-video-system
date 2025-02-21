from src.database import get_mysql_db

from sqlalchemy import text


def get_student_deployment_details(deployment_id: int):
    query = """
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
    result = db.execute(
        text(query),
        {
            "deployment_id": deployment_id
        }
    ).fetchall()
    return result
