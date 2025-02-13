import requests
import csv

# GitHub API URL to search for Python repositories sorted by stars
GITHUB_API_URL = "https://api.github.com/search/repositories?q=language:python&sort=stars&order=desc"

def get_top_python_coders(token=None):
    """Fetch top 10 Python repositories from GitHub API, repository data, and commit frequency."""
    response = requests.get(GITHUB_API_URL)
    
    if response.status_code == 200:
        repositories = response.json()["items"]
        top_coders = []
        
        for repo in repositories[:70]:  # Get top 10 repositories
            Git_User_id = repo["id"]
            Git_URL = repo["owner"]["html_url"]
            Git_repo_name = repo["name"]
            Git_owner_name = repo["owner"]["login"]
            Type_of_User = repo["owner"]["type"]
            GitHub_User_Since = repo["created_at"]
            Git_Score = repo["score"]
            stargazers_count = repo["stargazers_count"]
            fork_count = repo["forks_count"]

            # Fetch additional user details (including repo counts)
            email, hireable, bio, followers, public_repos, private_repos = get_user_details(Git_owner_name, token)

            # Get commit frequency
            commit_frequency = get_commit_frequency(Git_owner_name, Git_repo_name)

            # Append user details to dictionary
            top_coders.append({
                "Git_User_id": Git_User_id,
                "Git_URL": Git_URL,
                "Git_repo_name": Git_repo_name,
                "Git_owner_name": Git_owner_name,
                "Type_of_User": Type_of_User,
                "GitHub_User_Since": GitHub_User_Since,
                "Git_Score": Git_Score,
                "stargazers_count": stargazers_count,
                "fork_count": fork_count,
                "email": email,
                "hireable": hireable,
                "bio": bio,
                "followers": followers,
                "public_repos": public_repos,
                "private_repos": private_repos,
                "commit_frequency": commit_frequency
            })
        
        return top_coders
    else:
        return f"Error: {response.status_code}"


def get_user_details(username, token=None):
    """Fetch additional details of a GitHub user."""
    url = f"https://api.github.com/users/{username}"
    headers = {"Accept": "application/vnd.github.v3+json"}

     # If using authentication for private repos
    if token:
        headers["Authorization"] = f"token {token}"

    response = requests.get(url, headers=headers)


    
    if response.status_code == 200:
        user_data = response.json()
        email = user_data.get("email", "Not available")
        hireable = user_data.get("hireable", "Not available")
        bio = user_data.get("bio", "Not available")
        followers = user_data.get("followers", "Not available")
        public_repos = user_data.get("public_repos", 0)
        private_repos = 0
        if token:
            # Fetch the private repos (this requires token for authenticated users)
            repos_url = f"https://api.github.com/users/{username}/repos?type=all"
            repos_response = requests.get(repos_url, headers=headers)
            if repos_response.status_code == 200:
                private_repos = len([repo for repo in repos_response.json() if repo['private']])

        return email, hireable, bio, followers, public_repos, private_repos
    else:
         print(f"Error fetching data for {username}")

def get_commit_frequency(owner, repo_name):
    """Fetch commit frequency for a given repository."""
    commits_url = f"https://api.github.com/repos/{owner}/{repo_name}/commits"
    commits_response = requests.get(commits_url)
    
    if commits_response.status_code == 200:
        commits = commits_response.json()
        # Calculate commit frequency (simplified as commit count)
        commit_count = len(commits)
        return commit_count  # You can modify this to calculate frequency over time
    else:
        return 0  # If no commits are found or there's an error


def save_to_csv(data, filename="top_python_coders.csv"):
    """Save the extracted data to a CSV file."""
    if not data:
        print("No data to write to CSV.")
        return

    # Define CSV field names (headers)
    fieldnames = data[0].keys()

    # Write data to CSV file
    with open(filename, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()  # Write headers
        writer.writerows(data)  # Write data rows
    
    print(f"Data successfully written to {filename}")

if __name__ == "__main__":
    token = "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"
    top_coders = get_top_python_coders(token)

    
    
    if isinstance(top_coders, list):
        save_to_csv(top_coders)
    else:
        print(top_coders)
