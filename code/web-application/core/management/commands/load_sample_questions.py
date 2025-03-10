from django.core.management.base import BaseCommand
from core.models import CodingQuestion


class Command(BaseCommand):
    help = 'Loads sample coding questions into the database'

    def handle(self, *args, **options):
        self.stdout.write('Creating sample questions...')

        # Frontend Question
        frontend_question = CodingQuestion.objects.create(
            title="Create a Responsive Navigation Menu",
            description="""
# Responsive Navigation Bar Challenge

Design a responsive navigation bar that transitions from a horizontal menu on desktop to a hamburger menu on mobile devices.

## Requirements:

1. Create a horizontal navigation bar with 4-5 menu items for desktop view
2. For mobile devices (width < 768px), transform it into a hamburger menu
3. When the hamburger icon is clicked on mobile, the menu should toggle (show/hide)
4. Apply smooth transitions and animations
5. Use flexbox or grid for layout
6. Style it with a professional color scheme
7. Ensure the navigation is accessible (proper aria attributes, keyboard navigation)

## Evaluation Criteria:
- Code organization and cleanliness
- Responsiveness across different screen sizes
- Animation smoothness
- Accessibility implementation
- Design aesthetics
""",
            question_type="FRONTEND",
            difficulty="MEDIUM",
            example_input="N/A - This is a UI development challenge",
            example_output="N/A - The output should be a responsive navigation menu as described",
            constraints="Use only HTML, CSS, and JavaScript (no frameworks)",
            starter_code_html="""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Responsive Navigation</title>
    <link rel="stylesheet" href="styles.css">
</head>
<body>
    <!-- Add your navigation code here -->
    <nav class="navbar">
        <!-- Your navigation code goes here -->
    </nav>

    <main>
        <h1>Main Content Area</h1>
        <p>Resize the browser window to see the navigation change.</p>
    </main>

    <script src="script.js"></script>
</body>
</html>
""",
            starter_code_css="""/* Write your CSS here */
* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: 'Arial', sans-serif;
}

/* Add your navigation styles here */
""",
            starter_code_javascript="""// Write your JavaScript here
document.addEventListener('DOMContentLoaded', function() {
    // Your code for toggling the hamburger menu goes here
});
"""
        )
        self.stdout.write(self.style.SUCCESS(f'Created frontend question: {frontend_question.title}'))

        # Backend Question
        backend_question = CodingQuestion.objects.create(
            title="Implement a Rate Limiter",
            description="""
# Rate Limiter Implementation

Implement a rate limiting system that restricts the number of API requests a client can make within a specific time window.

## Requirements:

1. Create a class `RateLimiter` with the following methods:
   - `__init__(self, requests_per_minute)`: Constructor with the maximum allowed requests per minute
   - `is_allowed(self, client_id)`: Returns True if the request is allowed, False otherwise

2. The system should:
   - Allow up to `requests_per_minute` requests per minute for each unique client
   - Keep track of requests across multiple clients using the client_id
   - Clean up old request data to prevent memory leaks

## Example:
limiter = RateLimiter(3) # Allow 3 requests per minute
limiter.is_allowed("client1") # Returns True (1st request)
limiter.is_allowed("client1") # Returns True (2nd request)
limiter.is_allowed("client1") # Returns True (3rd request)
limiter.is_allowed("client1") # Returns False (exceeds limit)
limiter.is_allowed("client2") # Returns True (different client)

## Notes:
- Use an efficient data structure to store and check request timestamps
- Ensure thread safety if applicable in your implementation
- Consider edge cases like clock skew, system restarts, etc.
""",
            question_type="BACKEND",
            difficulty="MEDIUM",
            example_input="See example code in the description",
            example_output="See example code in the description",
            constraints="The solution should be efficient with O(1) lookup time",
            starter_code_python="""from collections import defaultdict
import time

class RateLimiter:
    def __init__(self, requests_per_minute):
        \"\"\"
        Initialize a rate limiter that allows a maximum number of requests per minute

        Args:
            requests_per_minute (int): Maximum requests allowed per minute per client
        \"\"\"
        # Your code here
        pass

    def is_allowed(self, client_id):
        \"\"\"
        Check if a request from the given client is allowed

        Args:
            client_id (str): Unique identifier for the client

        Returns:
            bool: True if the request is allowed, False otherwise
        \"\"\"
        # Your code here
        pass


# Example usage (uncomment for testing)
# limiter = RateLimiter(3)  # 3 requests per minute
# print(limiter.is_allowed("client1"))  # True
# print(limiter.is_allowed("client1"))  # True
# print(limiter.is_allowed("client1"))  # True
# print(limiter.is_allowed("client1"))  # False
# print(limiter.is_allowed("client2"))  # True
"""
        )
        self.stdout.write(self.style.SUCCESS(f'Created backend question: {backend_question.title}'))

        # Database Question
        database_question = CodingQuestion.objects.create(
            title="Design a Social Media Database Schema",
            description="""
# Social Media Database Design Challenge

Design a database schema for a simple social media platform with the following features:

## Features to Support:

1. User profiles with basic information
2. Posts containing text and optional media attachments
3. Comments on posts
4. Likes on posts and comments
5. Friend/follow relationships between users
6. User notifications

## Requirements:

1. Create table definitions with appropriate columns, data types, and constraints
2. Define primary keys and foreign key relationships
3. Add indexes where appropriate for performance
4. Write SQL queries for the following operations:
   - Get all posts from a user's friends/follows, ordered by date (newest first)
   - Find the most commented post in the last 7 days
   - Get a list of users who both liked and commented on a specific post

## Evaluation Criteria:
- Database schema design efficiency
- Appropriate use of relationships and constraints
- Query performance considerations
- SQL syntax and best practices
""",
            question_type="DATABASE",
            difficulty="MEDIUM",
            example_input="N/A - This is a database design challenge",
            example_output="Example table structure and sample queries",
            constraints="Use standard SQL that would work in PostgreSQL",
            starter_code_sql="""-- Create your tables here
CREATE TABLE users (
    id SERIAL PRIMARY KEY 
    -- Define user table columns
);

CREATE TABLE posts (
    id SERIAL PRIMARY KEY 
    -- Define posts table columns
);

-- Add more tables as needed

-- Write your queries below

-- 1. Get all posts from a user's friends/follows, ordered by date (newest first)
-- Replace 'user_id' with the actual parameter


-- 2. Find the most commented post in the last 7 days


-- 3. Get a list of users who both liked and commented on a specific post
-- Replace 'post_id' with the actual parameter

"""
        )
        self.stdout.write(self.style.SUCCESS(f'Created database question: {database_question.title}'))

        self.stdout.write(self.style.SUCCESS('Successfully loaded sample questions!'))