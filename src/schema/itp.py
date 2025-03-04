# src/schema/itp.py
from datetime import date
from typing import Dict, List, Optional
from pydantic import BaseModel

# TODO: Figure out proper ScriptPrompData attributes and ordering.
# TODO: StudentDeploymentDetails may need to be simplified. Or it may be uneccessary abstaction


# Summary Models
class StudentStepSummary(BaseModel):
    """Summary of a student's performance on a deployment step"""
    step_name: Optional[str] = None
    score: Optional[float] = None


class StudentComponentSummary(BaseModel):
    """Summary of a student's performance on a deployment component"""
    component_category: str
    score: Optional[float] = None
    steps: List[StudentStepSummary] = []


# Student Info Models
class Student(BaseModel):
    """Student information"""
    first_name: str
    last_name: str
    email: str
    tech_experience_id: Optional[int] = None
    employment_status_id: Optional[int] = None

    @property
    def full_name(self) -> str:
        """Get student's full name"""
        return f"{self.first_name} {self.last_name}"

    class Config:
        orm_mode = True


class Cohort(BaseModel):
    """Cohort information"""
    id: int
    name: str
    start_date: date
    end_date: date

    model_config = {"from_attributes": True}


# Deployment Package Models (Template information)
class DeploymentPackage(BaseModel):
    """Information about the deployment package"""
    id: int
    name: str
    notes: Optional[str] = None
    objectives: Optional[str] = None
    prompt: Optional[str] = None

    class Config:
        orm_mode = True


# Student-specific deployment data
class StudentDeploymentStep(StudentStepSummary):
    """Details of a student's performance on a specific deployment step"""
    grading: Optional[str] = None
    grading_data: Optional[str] = None
    objectives: Optional[str] = None
    instructions: Optional[str] = None
    deployment_component_id: Optional[int] = None
    component_category: Optional[str] = None

    class Config:
        orm_mode = True


class StudentDeploymentComponent(StudentComponentSummary):
    """Details of a student's performance on a specific deployment component"""
    id: int
    description: Optional[str] = None
    grading: Optional[str] = None
    steps: List[StudentDeploymentStep] = []

    @property
    def summary(self) -> StudentComponentSummary:
        """Return a simplified version with just the summary fields"""
        return StudentComponentSummary(
            component_category=self.component_category,
            score=self.score,
            steps=[
                StudentStepSummary(step_name=step.step_name, score=step.score)
                for step in self.steps
            ],
        )

    class Config:
        orm_mode = True


class StudentDeployment(BaseModel):
    """Basic information about a student's deployment instance"""
    id: int
    start_date: date
    end_date: date

    # Scores assigned to this specific student deployment
    acc_grading: Optional[str] = None
    acc_score: Optional[float] = None
    otd_grading: Optional[str] = None
    otd_score: Optional[float] = None
    opt_grading: Optional[str] = None
    opt_score: Optional[float] = None
    func_grading: Optional[str] = None
    func_score: Optional[float] = None

    # Reference to the package template
    package_id: int

    # Components and their steps
    components: List[StudentDeploymentComponent] = []

    model_config = {"from_attributes": True}

    @property
    def components_summary(self) -> Dict[str, StudentComponentSummary]:
        """Get summaries of all components as a dictionary."""
        return {
            component.component_category: component.summary
            for component in self.components
        }


class StudentDeploymentDetails(BaseModel):
    """Comprehensive details about a student's deployment with related data"""
    # Basic student info
    student: Student

    # Cohort info
    cohort: Cohort

    # Basic deployment info
    deployment: StudentDeployment

    # Package template info
    package: DeploymentPackage


class CohortComparison(BaseModel):
    """Metrics comparing a student to their cohort"""
    total_students: int
    students_below_or_equal: int
    cohort_avg_acc_score: float
    percentile: float
    rank: str

    @property
    def formatted_percentile(self) -> str:
        """Return formatted percentile as string"""
        return f"{self.percentile:.1f}" if self.percentile is not None else "N/A"


class ScriptPromptData(BaseModel):
    """
    Complete dataset used for generating script prompts.
    Combines student, cohort, deployment details and comparison data.
    """
    deployment_details: StudentDeploymentDetails
    cohort_comparison: Optional[CohortComparison] = None
    components_summary: Optional[List]

    def get_simple_components_text(self) -> str:
        """Return components as formatted text"""
        lines = []
        for (
            comp
        ) in (
            self.components_summary
        ):
            score = comp["score"] if comp["score"] is not None else "N/A"
            lines.append(f"• {comp['component_category']} {score}")
        return "\n".join(lines)

    def get_simple_steps_text(self) -> str:
        """Return steps as formatted text"""
        lines = []
        for (
            comp
        ) in (
            self.components_summary
        ):  # Changed from self.deployment_details.components_summary
            for step in comp["steps"]:
                score = step["score"] if step["score"] is not None else "N/A"
                lines.append(f"  • {step['step_name']}: {score}")
            lines.append("")
        return "\n".join(lines)

    def get_top_and_bottom_steps_text(self, top_n: int = 4, bottom_n: int = 4) -> str:
        """
        Get the top and bottom scored steps in a simple text format.

        Args:
            top_n (int): Number of top scores to include.
            bottom_n (int): Number of bottom scores to include.

        Returns:
            Formatted text with top and bottom steps.
        """
        # Extract all steps and their scores
        all_steps = []
        for (
            comp
        ) in (
            self.components_summary
        ):
            for step in comp["steps"]:
                all_steps.append(
                    (
                        step["step_name"],
                        step["score"] if step["score"] is not None else float("-inf"),
                    )
                )

        # Sort steps by score (descending order)
        sorted_steps = sorted(all_steps, key=lambda x: x[1], reverse=True)

        # Get top and bottom steps
        top_steps = sorted_steps[:top_n]
        bottom_steps = sorted_steps[-bottom_n:] if len(sorted_steps) > bottom_n else []

        # Format the results
        lines = []
        lines.append("High Scoring Steps:")
        for step_name, score in top_steps:
            lines.append(f"  • {step_name}: {score if score != float('-inf') else 'N/A'}")

        lines.append("\nLow Scoring Steps:")
        for step_name, score in bottom_steps:
            lines.append(f"  • {step_name}: {score if score != float('-inf') else 'N/A'}")

        return "\n".join(lines)
