# src/templates/feedback_script.py
class FeedbackScript:
    @staticmethod
    def create_intro_scene(data: dict) -> dict:
        return {
            "text": f"""Hi {data['student_name']}. Thanks for completing workload {data['workload_number']}. 
                       Your overall grade is {data['overall_score']} out of 5."""
        }

    @staticmethod
    def create_context_scene(data: dict) -> dict:
        return {
            "text": f"""This workload focused on containerization and deployment practices. 
                       The business objective was to containerize an application for an e-commerce company
                       before deploying it to an AWS Cloud Infrastructure that is secure, available, 
                       and fault tolerant."""
        }

    @staticmethod
    def create_career_scene(data: dict) -> dict:
        # Could be customized based on student's career interest
        return {
            "text": f"""his workload was important 
                       because it emphasizes several key skills..."""
        }

    @staticmethod
    def create_performance_scene(data: dict) -> dict:
        prev_scores = ", ".join(map(str, data["previous_scores"]))
        return {
            "text": f"""Your score of {data['overall_score']} shows improvement from your previous 
                       scores of {prev_scores}..."""
        }

    @staticmethod
    def create_component_scene(data: dict) -> dict:
        components_text = "\n".join(
            [
                f"Component {comp['name']}: Score - {comp['score']}/5"
                for comp in data["components"]
            ]
        )
        return {
            "text": f"""Let's examine your score. Your work was evaluated based on these components:
                       {components_text}"""
        }

    @staticmethod
    def create_feedback_scene(data: dict) -> dict:
        return {
            "text": (
                data["acc_grading"]
                if data["acc_grading"]
                else "No detailed feedback available."
            )
        }

    @staticmethod
    def create_closing_scene(data: dict) -> dict:
        return {
            "text": """Next steps:
                      1. Review the suggested materials
                      2. Focus on improvement areas
                      3. Consider joining upcoming study groups"""
        }

    @classmethod
    def generate_all_scenes(cls, data: dict) -> list:
        """Generate all scenes in order"""
        return [
            cls.create_intro_scene(data),
            cls.create_context_scene(data),
            cls.create_career_scene(data),
            cls.create_performance_scene(data),
            cls.create_component_scene(data),
            cls.create_feedback_scene(data),
            cls.create_closing_scene(data),
        ]
