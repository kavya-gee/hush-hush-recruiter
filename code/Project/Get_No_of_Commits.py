import requests
import os
import csv

# GitHub credentials (use environment variables for security)
TOKEN = "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"  # Set your GitHub token as an environment variable
HEADERS = {"Authorization": f"Bearer {TOKEN}"}
GRAPHQL_URL = "https://api.github.com/graphql"

def run_graphql_query(query, variables):
    response = requests.post(
        GRAPHQL_URL,
        json={"query": query, "variables": variables},
        headers=HEADERS
    )
    response.raise_for_status()
    data = response.json()
    if 'errors' in data:
        print("GraphQL Errors:", data['errors'])
        return None
    return data

def get_commit_count(owner, repo, contributor_id):
    query = """
    query($owner: String!, $repo: String!, $contributor_id: ID!) {
      repository(owner: $owner, name: $repo) {
        defaultBranchRef {
          name
          target {
            ... on Commit {
              history(author: {id: $contributor_id}) {
                totalCount
                nodes {
                  message
                }
              }
            }
          }
        }
      }
    }
    """
    variables = {
        "owner": owner,
        "repo": repo,
        "contributor_id": contributor_id
    }
    result = run_graphql_query(query, variables)
    if not result:
        return 0

   

    # Extract the total commit count
    repository_data = result.get('data', {}).get('repository', {})
    if not repository_data:
        print("Repository not found or inaccessible.")
        return 0

    default_branch_ref = repository_data.get('defaultBranchRef', {})
    if not default_branch_ref:
        print("Default branch not found.")
        return 0

    history = default_branch_ref.get('target', {}).get('history', {})
    return history.get('totalCount', 0)


# Function to process repositories and update contributor details
def process_repositories(top_50_repos_csv, base_folder):
    with open(top_50_repos_csv, mode='r', encoding='utf-8') as repos_file:
        repos_reader = csv.DictReader(repos_file)
        for repo_row in repos_reader:
            owner = repo_row['Repo Owner']
            repo = repo_row['Repo Name']
            print(f"Processing repository: {owner}/{repo}")

            # Path to the contributors_details.csv file
            contributors_csv_path = os.path.join(base_folder, f"{owner}_{repo}", "contributors_details.csv")
            if not os.path.exists(contributors_csv_path):
                print(f"Contributors file not found for {owner}/{repo}. Skipping...")
                continue

            # Read the contributors_details.csv file
            with open(contributors_csv_path, mode='r', encoding="utf-8") as contributors_file:
                contributors_reader = csv.DictReader(contributors_file)
                contributors_data = list(contributors_reader)

            # Update the Number_of_Commits column for each contributor
            for contributor_row in contributors_data:
                contributor_id = contributor_row['Git_Contributor_ID']
                commit_count = get_commit_count(owner, repo, contributor_id)
                contributor_row['Number_of_Commits'] = commit_count
                print(f"Updated commits for contributor {contributor_id}: {commit_count}")

            # Write the updated data back to the contributors_details.csv file
            with open(contributors_csv_path, mode='w', encoding='utf-8', newline='') as contributors_file:
                fieldnames = contributors_reader.fieldnames
                if 'Number_of_Commits' not in fieldnames:
                    fieldnames.append('Number_of_Commits')
                writer = csv.DictWriter(contributors_file, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(contributors_data)

            print(f"Updated contributors_details.csv for {owner}/{repo}")

# Main execution
if __name__ == "__main__":
    # Path to the top_50_repos.csv file
    top_50_repos_csv = "top_50_repos.csv"  # Replace with the actual path
    # Base folder containing "repo owner_repo name" folders
    base_folder = ""  # Replace with the actual path

    # Process repositories and update contributor details
    process_repositories(top_50_repos_csv, base_folder)