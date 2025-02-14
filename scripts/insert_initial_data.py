# scripts/bootstrap_initial_data.py
from src.models.schema import ScoreRange, Template, TemplateContent
from src.models.database import SessionLocalSQLite

db = SessionLocalSQLite()

# Create score ranges
ranges = [
    ScoreRange(name="Low", min_score=0.0, max_score=1.9),
    ScoreRange(name="Mid", min_score=2.0, max_score=3.9),
    ScoreRange(name="High", min_score=4.0, max_score=5.0),
]
db.add_all(ranges)
db.commit()

# Create template
template = Template(
    deployment_package_id=30,  # Your workload ID
    synthesia_template_id="d96a664e-dcbe-4b46-9a4e-7ffd80258e60",
    variables={
        "first_name": "first_name",
        "last_name": "last_name",
        "overall_score": "overall_score",
        "segment_1_range_1": "segment_1_range_low",
        "segment_1_range_2": "segment_1_range_mid",
        "segment_1_range_3": "segment_1_range_high",
    },
)
db.add(template)
db.commit()

# Define content for each range
range_content = {
    "Low": "This shows areas that need more focus and practice. Let's look at what you can improve.",
    "Mid": "This shows good understanding with some areas where you can deepen your knowledge.",
    "High": "This demonstrates excellent mastery of the material. Great work!",
}

# Create content for each range
for range_obj in ranges:
    content = TemplateContent(
        template_id=template.id,
        score_range_id=range_obj.id,
        variable_name=f"segment_1_range_{range_obj.name.lower()}",
        content=range_content[range_obj.name],
        score_type="overall"
    )
    db.add(content)
db.commit()
