import os
import json
import tempfile
import shutil
import logging
import subprocess
from django.utils import timezone
from typing import Dict, Any, Tuple

from .models import Assessment, CodingQuestion

logger = logging.getLogger(__name__)


def prepare_test_data(question: CodingQuestion) -> Tuple[str, Dict[str, Any]]:
    temp_dir = tempfile.mkdtemp(prefix="evaluation_")

    if question.question_type == "BACKEND":
        test_data = {
            "function_name": "is_allowed",
            "test_cases": [
                {"input": ["client1"], "expected_output": True},
                {"input": ["client1"], "expected_output": True},
                {"input": ["client1"], "expected_output": True},
                {"input": ["client1"], "expected_output": False},
                {"input": ["client2"], "expected_output": True},
            ]
        }

    elif question.question_type == "FRONTEND":
        test_data = {
            "html_required_elements": ["nav", "ul", "li", "button"],
            "css_required_properties": ["display: flex", "media"],
            "js_required_functionality": ["addEventListener", "toggle"]
        }

    elif question.question_type == "DATABASE":
        schema_file = os.path.join(temp_dir, "schema.sql")

        with open(schema_file, "w") as f:
            f.write("""
            DROP TABLE IF EXISTS users CASCADE;
            DROP TABLE IF EXISTS posts CASCADE;
            DROP TABLE IF EXISTS comments CASCADE;
            DROP TABLE IF EXISTS likes CASCADE;

            CREATE TABLE users (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100),
                email VARCHAR(100) UNIQUE
            );

            CREATE TABLE posts (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id),
                content TEXT,
                created_at TIMESTAMP DEFAULT NOW()
            );

            CREATE TABLE comments (
                id SERIAL PRIMARY KEY,
                post_id INTEGER REFERENCES posts(id),
                user_id INTEGER REFERENCES users(id),
                content TEXT,
                created_at TIMESTAMP DEFAULT NOW()
            );

            CREATE TABLE likes (
                id SERIAL PRIMARY KEY,
                post_id INTEGER REFERENCES posts(id),
                user_id INTEGER REFERENCES users(id),
                created_at TIMESTAMP DEFAULT NOW()
            );

            -- Insert sample data
            INSERT INTO users (name, email) VALUES 
                ('User 1', 'user1@example.com'),
                ('User 2', 'user2@example.com'),
                ('User 3', 'user3@example.com');

            INSERT INTO posts (user_id, content, created_at) VALUES 
                (1, 'Post 1 content', NOW() - INTERVAL '5 days'),
                (2, 'Post 2 content', NOW() - INTERVAL '3 days'),
                (3, 'Post 3 content', NOW() - INTERVAL '1 day');

            INSERT INTO comments (post_id, user_id, content, created_at) VALUES 
                (1, 2, 'Comment on post 1', NOW() - INTERVAL '4 days'),
                (1, 3, 'Another comment on post 1', NOW() - INTERVAL '3 days'),
                (2, 1, 'Comment on post 2', NOW() - INTERVAL '2 days');

            INSERT INTO likes (post_id, user_id, created_at) VALUES 
                (1, 2, NOW() - INTERVAL '4 days'),
                (1, 3, NOW() - INTERVAL '3 days'),
                (2, 3, NOW() - INTERVAL '2 days');
            """)

        test_data = {
            "schema_file": schema_file,
            "test_cases": [
                {
                    "query": "SELECT p.* FROM posts p JOIN likes l ON p.id = l.post_id WHERE l.user_id = 3 ORDER BY p.created_at DESC;",
                    "expected_result": [
                        {"id": 2, "user_id": 2, "content": "Post 2 content"},
                        {"id": 1, "user_id": 1, "content": "Post 1 content"}
                    ]
                }
            ]
        }

    else:
        test_data = {"test_cases": []}

    test_data_file = os.path.join(temp_dir, "test_data.json")
    with open(test_data_file, "w") as f:
        json.dump(test_data, f)

    return test_data_file, test_data


def evaluate_submission(assessment: Assessment) -> Dict[str, Any]:
    assessment.evaluation_status = 'EVALUATING'
    assessment.evaluation_started_at = timezone.now()
    assessment.save()

    try:
        question = assessment.chosen_question
        code_language = assessment.code_language
        code_submission = assessment.code_submission

        temp_dir = tempfile.mkdtemp(prefix="evaluation_")

        code_file = os.path.join(temp_dir, f"submission.{code_language}")
        with open(code_file, "w") as f:
            f.write(code_submission)

        test_data_file, _ = prepare_test_data(question)
        output_file = os.path.join(temp_dir, "output.json")
        timeout = 30

        docker_cmd = [
            "docker", "run", "--rm",
            "--network=none",  # Disable network access
            "--cpus=0.5",  # Limit CPU usage
            "--memory=512m",  # Limit memory usage
            # "--volume", f"{temp_dir}:.\workspace",  # Mount the temp directory
            "hushhushevaluator:latest",  # Docker image
            f"./workspace/submission.{code_language}",  # Code file
            code_language,  # Language
            f"./workspace/{os.path.basename(test_data_file)}",  # Test data file
            "./workspace/output.json",  # Output file
            str(timeout)  # Timeout in seconds
        ]
        subprocess.run(docker_cmd, check=True)

        with open(output_file, "r") as f:
            evaluation_results = json.load(f)

        assessment.evaluation_status = 'EVALUATED'
        assessment.evaluation_score = evaluation_results.get('evaluation_score', 0)
        assessment.evaluation_results = evaluation_results
        assessment.evaluation_completed_at = timezone.now()
        assessment.save()

        shutil.rmtree(temp_dir)
        return evaluation_results

    except Exception as e:
        logger.exception("Evaluation failed")

        assessment.evaluation_status = 'FAILED'
        assessment.evaluation_results = {
            'status': 'error',
            'message': str(e)
        }
        assessment.evaluation_completed_at = timezone.now()
        assessment.save()

        return {
            'status': 'error',
            'message': str(e)
        }