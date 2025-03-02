# models.py
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Text,
    Date,
    DateTime,
    ForeignKey,
    Boolean,
)
from sqlalchemy.orm import relationship
from datetime import datetime

from src.database import Base


class Cohort(Base):
    __tablename__ = "itp_cohorts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(155), nullable=False, index=True)
    students_estimate = Column(Integer, nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    budget_per_student = Column(Float, nullable=False)
    created = Column(DateTime, nullable=False, default=datetime.utcnow)
    modified = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    students = relationship("Student", back_populates="cohort")


class Student(Base):
    __tablename__ = "itp_students"

    id = Column(Integer, primary_key=True, autoincrement=True)
    cohort_id = Column(Integer, ForeignKey("itp_cohorts.id"), nullable=False)
    lmsid = Column(Integer, nullable=True)
    first_name = Column(String(155), nullable=False, index=True)
    last_name = Column(String(155), nullable=False, index=True)
    gender_id = Column(Integer, nullable=False)
    age_id = Column(Integer, nullable=False)
    background_id = Column(Integer, nullable=False)
    employment_status_id = Column(Integer, nullable=True)
    tech_experience_id = Column(Integer, nullable=True)
    student_placement_id = Column(Integer, nullable=True)
    email = Column(String(155), nullable=False)
    telephone = Column(String(20), nullable=False)
    address_line_1 = Column(String(50), nullable=False)
    address_line_2 = Column(String(50), nullable=True)
    city = Column(String(50), nullable=False)
    state = Column(String(20), nullable=True)
    zip = Column(String(30), nullable=True)
    country_id = Column(Integer, nullable=False)
    create_instance = Column(Boolean, nullable=False, default=False)
    aws_account_name = Column(String(50), nullable=True)
    aws_temp_pass = Column(String(50), nullable=True)
    disabled = Column(Boolean, nullable=False, default=False)
    aws_account_status = Column(String(50), nullable=True)
    aws_accountid = Column(String(50), nullable=True)
    service_control_policy_id = Column(Integer, nullable=True)
    aws_instance_name = Column(String(50), nullable=True)
    aws_instance_status = Column(String(50), nullable=True)
    aws_instanceid = Column(String(50), nullable=True)
    aws_instance_ip = Column(String(30), nullable=True)
    for_instructor = Column(Boolean, nullable=True)
    github_user = Column(String(155), nullable=True)
    created = Column(DateTime, nullable=False, default=datetime.utcnow)
    modified = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    cohort = relationship("Cohort", back_populates="students")
    deployments = relationship("StudentDeployment", back_populates="student")


class DeploymentPackage(Base):
    __tablename__ = "itp_deployment_packages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, index=True)
    deployment_package_group_id = Column(Integer, nullable=True)
    deployment_group_id = Column(Integer, nullable=True)
    difficulty_id = Column(Integer, nullable=False)
    service_control_policy_id = Column(Integer, nullable=True)
    deployment_category = Column(Integer, nullable=False)
    deployment_type = Column(Integer, nullable=False)
    objectives = Column(Text, nullable=False)
    deliverables = Column(Text, nullable=True)
    tech_required = Column(Text, nullable=True)
    application_id = Column(Integer, nullable=False)
    infra_template_id = Column(Integer, nullable=False)
    notes = Column(Text, nullable=True)
    number_of_steps = Column(Integer, nullable=False)
    ip_score = Column(Float, nullable=True)
    sp_score = Column(Float, nullable=True)
    ep_score = Column(Float, nullable=True)
    origin_repo = Column(String(155), nullable=True)
    target_repo = Column(String(50), nullable=True)
    target_pipeline = Column(String(100), nullable=True)
    created = Column(DateTime, nullable=False, default=datetime.utcnow)
    modified = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    student_deployments = relationship(
        "StudentDeployment", back_populates="deployment_package"
    )
    package_steps = relationship(
        "DeploymentPackageStep", back_populates="deployment_package"
    )


class DeploymentComponent(Base):
    __tablename__ = "itp_deployment_components"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    created = Column(DateTime, nullable=False, default=datetime.utcnow)
    modified = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    student_deployment_components = relationship(
        "StudentDeploymentComponent", back_populates="deployment_component"
    )
    package_steps = relationship(
        "DeploymentPackageStep", back_populates="deployment_component"
    )


class StudentDeployment(Base):
    __tablename__ = "itp_student_deployments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    deployment_package_id = Column(
        Integer, ForeignKey("itp_deployment_packages.id"), nullable=False
    )
    student_id = Column(Integer, ForeignKey("itp_students.id"), nullable=False)
    student_group_id = Column(Integer, nullable=False)
    infra_template_id = Column(Integer, nullable=False)
    aws_account_name = Column(String(50), nullable=True)
    aws_account_status = Column(String(50), nullable=True)
    aws_accountid = Column(String(50), nullable=True)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    aws_temp_pass = Column(String(50), nullable=True)
    grade = Column(String(10), nullable=False)
    notes = Column(Text, nullable=False)
    acc_grading = Column(Text, nullable=True)
    acc_score = Column(Float, nullable=True)
    otd_grading = Column(Text, nullable=True)
    otd_score = Column(Float, nullable=True)
    opt_grading = Column(Text, nullable=True)
    opt_score = Column(Float, nullable=True)
    func_grading = Column(Text, nullable=True)
    func_score = Column(Float, nullable=True)
    acc_data = Column(Text, nullable=True)
    otd_data = Column(Text, nullable=True)
    opt_data = Column(Text, nullable=True)
    func_data = Column(Text, nullable=True)
    created = Column(DateTime, nullable=False, default=datetime.utcnow)
    modified = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    student = relationship("Student", back_populates="deployments")
    deployment_package = relationship(
        "DeploymentPackage", back_populates="student_deployments"
    )
    deployment_steps = relationship(
        "StudentDeploymentStep", back_populates="student_deployment"
    )
    deployment_components = relationship(
        "StudentDeploymentComponent", back_populates="student_deployment"
    )


class DeploymentPackageStep(Base):
    __tablename__ = "itp_deployment_package_steps"

    id = Column(Integer, primary_key=True, autoincrement=True)
    deployment_package_id = Column(
        Integer, ForeignKey("itp_deployment_packages.id"), nullable=False
    )
    deployment_step_id = Column(Integer, nullable=False)
    difficulty_id = Column(Integer, nullable=True)
    objective = Column(Text, nullable=True)
    instructions = Column(Text, nullable=True)
    grading_guide = Column(Text, nullable=True)
    max_score = Column(Integer, nullable=False)
    created = Column(DateTime, nullable=False, default=datetime.utcnow)
    modified = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    objective_prompt = Column(Text, nullable=True)
    grading_prompt = Column(Text, nullable=True)
    required_insert = Column(Text, nullable=True)
    component_name = Column(String(50), nullable=True)
    component_category = Column(String(50), nullable=True)
    target_file = Column(String(30), nullable=True)
    param_1 = Column(String(155), nullable=True)
    param_2 = Column(String(155), nullable=True)
    param_3 = Column(String(155), nullable=True)
    param_4 = Column(String(155), nullable=True)
    param_5 = Column(String(155), nullable=True)
    deployment_component_id = Column(
        Integer, ForeignKey("itp_deployment_components.id"), nullable=False
    )
    disabled = Column(Boolean, nullable=False, default=False)

    # Relationships
    deployment_package = relationship(
        "DeploymentPackage", back_populates="package_steps"
    )
    deployment_component = relationship(
        "DeploymentComponent", back_populates="package_steps"
    )
    student_deployment_steps = relationship(
        "StudentDeploymentStep", back_populates="deployment_package_step"
    )


class StudentDeploymentComponent(Base):
    __tablename__ = "itp_student_deployment_components"

    id = Column(Integer, primary_key=True, autoincrement=True)
    student_deployment_id = Column(
        Integer, ForeignKey("itp_student_deployments.id"), nullable=False
    )
    deployment_component_id = Column(
        Integer, ForeignKey("itp_deployment_components.id"), nullable=False
    )
    deployment_package_id = Column(Integer, nullable=False)
    score = Column(Float, nullable=True)
    grading = Column(Text, nullable=True)
    created = Column(DateTime, nullable=False, default=datetime.utcnow)
    modified = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    student_deployment = relationship(
        "StudentDeployment", back_populates="deployment_components"
    )
    deployment_component = relationship(
        "DeploymentComponent", back_populates="student_deployment_components"
    )
    student_deployment_steps = relationship(
        "StudentDeploymentStep", back_populates="student_deployment_component"
    )


class StudentDeploymentStep(Base):
    __tablename__ = "itp_student_deployment_steps"

    id = Column(Integer, primary_key=True, autoincrement=True)
    student_deployment_id = Column(
        Integer, ForeignKey("itp_student_deployments.id"), nullable=False
    )
    deployment_package_id = Column(Integer, nullable=False)
    deployment_package_step_id = Column(
        Integer, ForeignKey("itp_deployment_package_steps.id"), nullable=False
    )
    deployment_step_id = Column(Integer, nullable=False)
    student_deployment_component_id = Column(
        Integer, ForeignKey("itp_student_deployment_components.id"), nullable=False
    )
    difficulty_id = Column(Integer, nullable=True)
    objectives = Column(Text, nullable=True)
    instructions = Column(Text, nullable=True)
    grading = Column(Text, nullable=True)
    score = Column(Float, nullable=True)
    grading_data = Column(Text, nullable=True)
    created = Column(DateTime, nullable=False, default=datetime.utcnow)
    modified = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    student_deployment = relationship(
        "StudentDeployment", back_populates="deployment_steps"
    )
    deployment_package_step = relationship(
        "DeploymentPackageStep", back_populates="student_deployment_steps"
    )
    student_deployment_component = relationship(
        "StudentDeploymentComponent", back_populates="student_deployment_steps"
    )
