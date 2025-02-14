# scripts/bootstrap_initial_data.py
from src.models.schema import Template
from src.models.database import SessionLocalSQLite

db = SessionLocalSQLite()

template = Template(
    deployment_package_id=30,
    synthesia_template_id="d96a664e-dcbe-4b46-9a4e-7ffd80258e60",
    variables={
        "scene_1_text": "scene_1_text",
        "first_name": "first_name",
        "last_name": "last_name",
        "overall_score": "overall_score",
    },
)

db.add(template)
db.commit()
