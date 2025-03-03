# src/api/dependencies/db.py
import json

from typing import List, Optional, Union
from sqlalchemy import select, func
from sqlalchemy.engine import Row
from sqlalchemy.orm import aliased, joinedload
from sqlalchemy.sql import Select
from src.models.video import DeploymentPackageExt
from src.models.itp import (
    Student as ORMStudent,
    Cohort as ORMCohort,
    StudentDeployment as ORMStudentDeployment,
    DeploymentPackage as ORMDeploymentPackage,
    DeploymentComponent as ORMDeploymentComponent,
    StudentDeploymentComponent as ORMStudentDeploymentComponent,
    DeploymentPackageStep as ORMDeploymentPackageStep,
    StudentDeploymentStep as ORMStudentDeploymentStep,
)
from src.schema.itp import (
    Student,
    Cohort,
    DeploymentPackage,
    StudentDeployment,
    StudentDeploymentDetails,
    StudentDeploymentComponent,
    StudentDeploymentStep,
)
from src.database import get_mysql_db
from src.logging_config import app_logger


def select_student(
    student_id: int = None,
    student_deployment_id: int = None,
    to_pydantic: bool = True,
    execute: bool = True,
) -> Union[Student, ORMStudent, Row, Select]:
    """
    Fetch student information.

    Args:
        student_id: The ID of the student (optional if student_deployment_id provided)
        student_deployment_id: The ID of the student deployment (optional if student_id provided)
        to_pydantic: If True, returns a Pydantic model
        execute: If True, executes the query

    Returns:
        Student Pydantic model if to_pydantic=True and execute=True
        ORM Student model or Row if to_pydantic=False and execute=True
        SQLAlchemy Select object if execute=False
    """
    if not student_id and not student_deployment_id:
        raise ValueError("Either student_id or student_deployment_id must be provided")

    # Build the SQLAlchemy query
    query = select(ORMStudent)

    if student_deployment_id:
        query = query.join(
            ORMStudentDeployment, ORMStudent.id == ORMStudentDeployment.student_id
        ).where(ORMStudentDeployment.id == student_deployment_id)
    else:
        query = query.where(ORMStudent.id == student_id)

    # Return query if not executing
    if not execute:
        return query

    # Execute the query
    db = next(get_mysql_db())
    result = db.execute(query).scalars().first()

    if not result:
        return None

    # Return ORM model if not converting to Pydantic
    if not to_pydantic:
        return result

    # Convert to Pydantic model
    return Student.from_orm(result)


def select_cohort(
    cohort_id: int = None,
    student_id: int = None,
    student_deployment_id: int = None,
    to_pydantic: bool = True,
    execute: bool = True,
) -> Union[Cohort, ORMCohort, Row, Select]:
    """
    Fetch cohort information.

    Args:
        cohort_id: The ID of the cohort (optional if other IDs provided)
        student_id: The ID of the student (optional)
        student_deployment_id: The ID of the student deployment (optional)
        to_pydantic: If True, returns a Pydantic model
        execute: If True, executes the query

    Returns:
        Cohort Pydantic model if to_pydantic=True and execute=True
        ORM Cohort model or Row if to_pydantic=False and execute=True
        SQLAlchemy Select object if execute=False
    """
    if not any([cohort_id, student_id, student_deployment_id]):
        raise ValueError("At least one ID parameter must be provided")

    # Build the SQLAlchemy query
    query = select(ORMCohort)

    if cohort_id:
        query = query.where(ORMCohort.id == cohort_id)
    elif student_id:
        query = query.join
        (
            ORMStudent, ORMCohort.id == ORMStudent.cohort_id).where
        (
            ORMStudent.id == student_id
        )
    else:
        query = (
            query.join(ORMStudent, ORMCohort.id == ORMStudent.cohort_id)
            .join
            (
                ORMStudentDeployment, ORMStudent.id == ORMStudentDeployment.student_id
            )
            .where(ORMStudentDeployment.id == student_deployment_id)
        )

    # Return query if not executing
    if not execute:
        return query

    # Execute the query
    db = next(get_mysql_db())
    result = db.execute(query).scalars().first()

    if not result:
        return None

    # Return ORM model if not converting to Pydantic
    if not to_pydantic:
        return result

    # Convert to Pydantic model
    return Cohort.from_orm(result)


def select_deployment_package(
    package_id: int, to_pydantic: bool = True, execute: bool = True
) -> Union[DeploymentPackage, ORMDeploymentPackage, Row, Select]:
    """
    Fetch deployment package template information.

    Args:
        package_id: The ID of the deployment package
        to_pydantic: If True, returns a Pydantic model
        execute: If True, executes the query

    Returns:
        DeploymentPackage Pydantic model if to_pydantic=True and execute=True
        ORM DeploymentPackage model or Row if to_pydantic=False and execute=True
        SQLAlchemy Select object if execute=False
    """
    # Build the query
    query = select(ORMDeploymentPackage).where(ORMDeploymentPackage.id == package_id)

    # Return query if not executing
    if not execute:
        return query

    # Execute the query
    db = next(get_mysql_db())
    result = db.execute(query).scalars().first()

    if not result:
        return None

    # Return ORM model if not converting to Pydantic
    if not to_pydantic:
        return result

    # Convert to Pydantic model
    return DeploymentPackage.from_orm(result)


def select_student_deployment(
    student_deployment_id: int, to_pydantic: bool = True, execute: bool = True
) -> Union[StudentDeployment, ORMStudentDeployment, Row, Select]:
    """
    Fetch basic student deployment information (without components).

    Args:
        student_deployment_id: The ID of the student deployment
        to_pydantic: If True, returns a Pydantic model
        execute: If True, executes the query

    Returns:
        StudentDeployment Pydantic model if to_pydantic=True and execute=True
        ORM StudentDeployment model or Row if to_pydantic=False and execute=True
        SQLAlchemy Select object if execute=False
    """
    # Build the query
    query = select(ORMStudentDeployment).where(
        ORMStudentDeployment.id == student_deployment_id
    )

    # Return query if not executing
    if not execute:
        return query

    # Execute the query
    db = next(get_mysql_db())
    result = db.execute(query).scalars().first()

    if not result:
        return None

    # Return ORM model if not converting to Pydantic
    if not to_pydantic:
        return result

    # Convert to Pydantic model
    return StudentDeployment.from_orm(result)


def select_deployment_components(
    student_deployment_id: int,
    include_steps: bool = True,
    to_pydantic: bool = True,
    execute: bool = True,
) -> Union[
    List[StudentDeploymentComponent],
    List[ORMStudentDeploymentComponent],
    List[Row],
    Select,
]:
    """
    Fetch components for a student deployment.

    Args:
        student_deployment_id: The ID of the student deployment
        include_steps: Whether to include steps in the query
        to_pydantic: If True, returns Pydantic models
        execute: If True, executes the query

    Returns:
        List of StudentDeploymentComponent Pydantic models if to_pydantic=True and execute=True
        List of ORM StudentDeploymentComponent models or Rows if to_pydantic=False and execute=True
        SQLAlchemy Select object if execute=False
    """
    # Build query for components
    query = (
        select(ORMStudentDeploymentComponent)
        .join(
            ORMDeploymentComponent,
            ORMStudentDeploymentComponent.deployment_component_id
            == ORMDeploymentComponent.id,
        )
        .where(
            ORMStudentDeploymentComponent.student_deployment_id == student_deployment_id
        )
    )

    # Add eager loading for steps if needed
    if include_steps:
        query = query.options(
            joinedload(ORMStudentDeploymentComponent.student_deployment_steps)
        )

    # Return query if not executing
    if not execute:
        return query

    # Execute the query
    db = next(get_mysql_db())
    results = db.execute(query).scalars().all()

    # Return ORM models if not converting to Pydantic
    if not to_pydantic:
        return results

    # Convert to Pydantic models
    components = []
    for comp_relation in results:
        comp = comp_relation.deployment_component

        # Create the component model
        component_model = StudentDeploymentComponent(
            id=comp.id,
            component_category=comp.title,
            description=comp.description,
            grading=comp_relation.grading,
            score=comp_relation.score,
            steps=[],
        )

        # Add steps if needed
        if include_steps:
            steps_query = (
                select(ORMStudentDeploymentStep)
                .join(
                    ORMDeploymentPackageStep,
                    ORMStudentDeploymentStep.deployment_package_step_id
                    == ORMDeploymentPackageStep.id,
                )
                .where(
                    ORMStudentDeploymentStep.student_deployment_component_id
                    == comp_relation.id
                )
            )

            step_results = db.execute(steps_query).scalars().all()

            for step in step_results:
                package_step = (
                    db.execute(
                        select(ORMDeploymentPackageStep).where(
                            ORMDeploymentPackageStep.id
                            == step.deployment_package_step_id
                        )
                    )
                    .scalars()
                    .first()
                )

                if package_step:
                    step_model = StudentDeploymentStep(
                        grading=step.grading,
                        score=step.score,
                        objectives=step.objectives,
                        instructions=step.instructions,
                        deployment_component_id=comp_relation.deployment_component_id,
                        step_name=package_step.component_name,
                        component_category=package_step.component_category,
                    )
                    component_model.steps.append(step_model)

        components.append(component_model)

    return components


def select_student_deployment_details(deployment_id: int, to_pydantic: bool = True):
    """
    Fetch student deployment details from the database using SQLAlchemy ORM and MySQL JSON functions.
    Structures the result to match the StudentDeploymentDetails Pydantic model.

    Args:
        deployment_id (int): The ID of the deployment to fetch details for.
        to_pydantic (bool): If True, returns the results as a Pydantic model. If False, returns raw query results.

    Returns:
        Union[StudentDeploymentDetails, dict]: The query results, either as a Pydantic model or a dictionary.
    """
    db = next(get_mysql_db())

    # Aliases for tables (same as before)
    s = aliased(ORMStudent)
    c = aliased(ORMCohort)
    d = aliased(ORMStudentDeployment)
    dc = aliased(ORMStudentDeploymentComponent)
    comp = aliased(ORMDeploymentComponent)
    ds = aliased(ORMStudentDeploymentStep)
    dps = aliased(ORMDeploymentPackageStep)
    dp = aliased(ORMDeploymentPackage)

    # The query implementation is the same as before
    # Construct the inner query for components and steps
    components_subquery = (
        select(
            # Student and cohort fields
            s.first_name,
            s.last_name,
            s.email,
            s.tech_experience_id,
            s.employment_status_id,
            c.id.label("cohort_id"),
            c.name.label("cohort_name"),
            c.start_date.label("cohort_start_date"),
            c.end_date.label("cohort_end_date"),
            # Deployment fields
            d.id.label("deployment_id"),
            d.start_date.label("deployment_start_date"),
            d.end_date.label("deployment_end_date"),
            d.acc_grading,
            d.acc_score,
            d.otd_grading,
            d.otd_score,
            d.opt_grading,
            d.opt_score,
            d.func_grading,
            d.func_score,
            d.deployment_package_id,
            # Component fields
            comp.id.label("component_id"),
            func.json_object(
                "id",
                comp.id,
                "component_category",
                comp.title,
                "description",
                comp.description,
                "grading",
                dc.grading,
                "score",
                dc.score,
                "steps",
                func.json_arrayagg(
                    func.json_object(
                        "step_name",
                        dps.component_name,
                        "grading",
                        ds.grading,
                        "score",
                        ds.score,
                        "objectives",
                        ds.objectives,
                        "instructions",
                        ds.instructions,
                        "deployment_component_id",
                        ds.student_deployment_component_id,
                        "component_category",
                        dps.component_category,
                    )
                ),
            ).label("component_json"),
            # Package fields
            func.json_object(
                "id",
                dp.id,
                "name",
                dp.name,
                "notes",
                dp.notes,
                "objectives",
                dp.objectives,
            ).label("deployment_package_json"),
        )
        .select_from(s)
        .join(c, s.cohort_id == c.id)
        .join(d, s.id == d.student_id)
        .outerjoin(dc, d.id == dc.student_deployment_id)
        .outerjoin(comp, dc.deployment_component_id == comp.id)
        .outerjoin(
            dps,
            (d.deployment_package_id == dps.deployment_package_id)
            & (dps.deployment_component_id == dc.deployment_component_id),
        )
        .outerjoin(
            ds,
            (d.id == ds.student_deployment_id)
            & (ds.deployment_step_id == dps.deployment_step_id),
        )
        .outerjoin(dp, d.deployment_package_id == dp.id)
        .where(d.id == deployment_id)
        .group_by(comp.id)  # Group steps by component
    ).subquery()

    # Outer query to aggregate components
    outer_query = select(
        components_subquery.c.first_name,
        components_subquery.c.last_name,
        components_subquery.c.email,
        components_subquery.c.tech_experience_id,
        components_subquery.c.employment_status_id,
        components_subquery.c.cohort_id,
        components_subquery.c.cohort_name,
        components_subquery.c.cohort_start_date,
        components_subquery.c.cohort_end_date,
        components_subquery.c.deployment_id,
        components_subquery.c.deployment_start_date,
        components_subquery.c.deployment_end_date,
        components_subquery.c.acc_grading,
        components_subquery.c.acc_score,
        components_subquery.c.otd_grading,
        components_subquery.c.otd_score,
        components_subquery.c.opt_grading,
        components_subquery.c.opt_score,
        components_subquery.c.func_grading,
        components_subquery.c.func_score,
        components_subquery.c.deployment_package_id,
        func.json_arrayagg(
            components_subquery.c.component_json
        ).label("components_data"),
        components_subquery.c.deployment_package_json.label("deployment_package_data"),
    ).group_by(
        components_subquery.c.deployment_id, components_subquery.c.deployment_package_id
    )

    # Execute the query
    result = db.execute(outer_query).fetchone()

    if not result:
        return None

    result_dict = {
        "student": {
            "first_name": result.first_name,
            "last_name": result.last_name,
            "email": result.email,
            "tech_experience_id": result.tech_experience_id,
            "employment_status_id": result.employment_status_id,
        },
        # Cohort info nested
        "cohort": {
            "id": result.cohort_id,
            "name": result.cohort_name,
            "start_date": result.cohort_start_date,
            "end_date": result.cohort_end_date,
        },
        # Nested deployment structure - this matches what your model expects
        "deployment": {
            "id": result.deployment_id,
            "start_date": result.deployment_start_date,
            "end_date": result.deployment_end_date,
            "acc_grading": result.acc_grading,
            "acc_score": result.acc_score,
            "otd_grading": result.otd_grading,
            "otd_score": result.otd_score,
            "opt_grading": result.opt_grading,
            "opt_score": result.opt_score,
            "func_grading": result.func_grading,
            "func_score": result.func_score,
            "package_id": result.deployment_package_id,
            "components": json.loads(result.components_data),
        },
        # Package info
        "package": json.loads(result.deployment_package_data),
    }

    if not to_pydantic:
        return result_dict

    # Convert to Pydantic model
    return StudentDeploymentDetails(**result_dict)


def select_cohort_scores(
    cohort_id: int, package_id: int, to_pydantic: bool = True, execute: bool = True
) -> Union[List[float], List[ORMStudentDeployment], List[Row], Select]:
    """
    Fetch cohort scores for calculating percentile.

    Args:
        cohort_id: The ID of the cohort
        package_id: The ID of the deployment package
        to_pydantic: If True, returns a list of float scores
        execute: If True, executes the query

    Returns:
        List of scores if to_pydantic=True and execute=True
        List of ORM StudentDeployment models or Rows if to_pydantic=False and execute=True
        SQLAlchemy Select object if execute=False
    """
    # Build the query for cohort scores
    query = (
        select(ORMStudentDeployment)
        .join(ORMStudent, ORMStudentDeployment.student_id == ORMStudent.id)
        .where(
            ORMStudent.cohort_id == cohort_id,
            ORMStudentDeployment.deployment_package_id == package_id,
            ORMStudentDeployment.acc_score.is_not(None),
        )
    )

    # Return query if not executing
    if not execute:
        return query

    # Execute the query
    db = next(get_mysql_db())
    results = db.execute(query).scalars().all()

    # Return ORM models if not converting to Pydantic
    if not to_pydantic:
        return results

    # Extract just the scores
    return [deployment.acc_score for deployment in results]


def select_deployment_package_extension(
        deployment_package_id: int,
        db
) -> DeploymentPackageExt:
    stmt = select(DeploymentPackageExt).where(
        DeploymentPackageExt.deployment_package_id == deployment_package_id
    )
    deployment_package: DeploymentPackageExt = db.execute(stmt).scalar_one()
    return deployment_package
