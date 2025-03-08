import csv
import requests
import os
import base64

# GitHub API token for authentication
GITHUB_TOKEN = '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'
HEADERS = {'Authorization': f'Bearer {GITHUB_TOKEN}'}

# GraphQL query to fetch pull requests and their contributors
GRAPHQL_QUERY = """
query ($owner: String!, $repo: String!, $cursor: String) {
  repository(owner: $owner, name: $repo) {
    pullRequests(first: 100, after: $cursor, states: [OPEN, CLOSED, MERGED]) {
      nodes {
        author {
          login
        }
        state
        merged
      }
      pageInfo {
        endCursor
        hasNextPage
      }
    }
  }
}
"""

# Function to decode Git_Contributor_ID
def decode_contributor_id(encoded_id):
    try:
        decoded_id = base64.b64decode(encoded_id).decode('utf-8')
        # Extract the user ID from the decoded string (e.g., "04:User5790321" -> 5790321)
        user_id = decoded_id.split('User')[-1]
        return user_id
    except:
        return None

# Function to fetch GitHub username from user ID
def get_github_username(user_id, token):
    url = f"https://api.github.com/user/{user_id}"
    headers = {'Authorization': f'Bearer {token}'}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        return data['login']
    return None

# Function to fetch all pull requests using GraphQL with pagination
def fetch_pull_requests_graphql(repo_owner, repo_name):
    pull_requests = []
    cursor = None
    has_next_page = True

    while has_next_page:
        variables = {
            "owner": repo_owner,
            "repo": repo_name,
            "cursor": cursor
        }
        response = requests.post(
            'https://api.github.com/graphql',
            json={'query': GRAPHQL_QUERY, 'variables': variables},
            headers=HEADERS
        )
        if response.status_code == 200:
            data = response.json()
            if 'errors' in data:
                print(f"GraphQL errors: {data['errors']}")
                break
            pr_data = data['data']['repository']['pullRequests']
            pull_requests.extend(pr_data['nodes'])
            page_info = pr_data['pageInfo']
            has_next_page = page_info['hasNextPage']
            cursor = page_info['endCursor']
        else:
            print(f"Failed to fetch pull requests for {repo_owner}/{repo_name}: {response.status_code}")
            break

    return pull_requests

# Function to read CSV file
def read_csv(file_path):
    with open(file_path, mode='r', encoding="utf-8") as file:
        return list(csv.DictReader(file))

# Function to write CSV file
def write_csv(file_path, data, fieldnames):
    with open(file_path, mode='w', encoding="utf-8", newline='') as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)

# Main function
def main():
    top_repos = read_csv('Top_50_repos.csv')
    
    for repo in top_repos:
        repo_owner = repo['Repo Owner']
        repo_name = repo['Repo Name']
        contributors_file = f"{repo_owner}_{repo_name}/Contributors_details.csv"
        
        if not os.path.exists(contributors_file):
            print(f"Contributors file not found for {repo_owner}/{repo_name}")
            continue
        
        contributors = read_csv(contributors_file)
        pull_requests = fetch_pull_requests_graphql(repo_owner, repo_name)
        
        # Initialize PR counts for each contributor
        contributor_pr_counts = {}
        for contributor in contributors:
            encoded_id = contributor['Git_Contributor_ID']
            user_id = decode_contributor_id(encoded_id)
            if user_id:
                username = get_github_username(user_id, GITHUB_TOKEN)
                if username:
                    contributor_pr_counts[username] = {'created': 0, 'merged': 0, 'closed': 0}
                    contributor['Git_Contributor_ID'] = username  # Update the CSV with the username
                else:
                    print(f"Failed to fetch GitHub username for user ID {user_id}")
            else:
                print(f"Failed to decode Git_Contributor_ID: {encoded_id}")
        
        # Process pull requests
        for pr in pull_requests:
            author = pr['author']
            if author and 'login' in author:  # Check if the author has a login field
                author_login = author['login']
                if author_login in contributor_pr_counts:
                    contributor_pr_counts[author_login]['created'] += 1
                    if pr['merged']:
                        contributor_pr_counts[author_login]['merged'] += 1
                    if pr['state'] == 'CLOSED' and not pr['merged']:
                        contributor_pr_counts[author_login]['closed'] += 1
                else:
                    print(f"Pull request author {author_login} not found in contributors.")
            else:
                print(f"Pull request author is not a User or has no login: {author}")
        
        # Debug: Print contributor PR counts
        print(f"Pull request counts for {repo_owner}/{repo_name}:")
        for author_login, counts in contributor_pr_counts.items():
            print(f"{author_login}: {counts}")
        
        # Update contributors with PR counts
        for contributor in contributors:
            author_login = contributor['Git_Contributor_ID']
            if author_login in contributor_pr_counts:
                contributor['PRs_Created'] = contributor_pr_counts[author_login]['created']
                contributor['PRs_Merged'] = contributor_pr_counts[author_login]['merged']
                contributor['PRs_Closed'] = contributor_pr_counts[author_login]['closed']
        
        # Write updated contributors data back to CSV
        fieldnames = contributors[0].keys()
        write_csv(contributors_file, contributors, fieldnames)

if __name__ == "__main__":
    main()