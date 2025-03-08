import requests
import csv
import os

# GitHub API endpoint
GITHUB_API_URL = "https://api.github.com/graphql"

# Your GitHub personal access token (store securely, avoid hardcoding in production)
GITHUB_TOKEN = "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"

# Headers for authentication
HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Content-Type": "application/json"
}

# GraphQL query to fetch additions and deletions for a contributor
GRAPHQL_QUERY = """
query($owner: String!, $repo: String!, $cursor: String, $contributor: ID!) {
  repository(owner: $owner, name: $repo) {
    defaultBranchRef {
      target {
        ... on Commit {
          history(first: 50, after: $cursor, author: { id: $contributor }) {
            totalCount
            pageInfo {
              endCursor
              hasNextPage
            }
            edges {
              node {
                additions
                deletions
              }
            }
          }
        }
      }
    }
  }
}
"""


def fetch_contributor_stats(owner, repo, contributor_id):
    """
    Fetches total additions and deletions for a contributor using GitHub's GraphQL API.
    Handles pagination to fetch all commits.
    """
    total_additions = 0
    total_deletions = 0
    cursor = None
    has_next_page = True

    while has_next_page:
        variables = {
            "owner": owner,
            "repo": repo,
            "contributor": contributor_id,
            "cursor": cursor
        }

        response = requests.post(
            GITHUB_API_URL,
            json={"query": GRAPHQL_QUERY, "variables": variables},
            headers=HEADERS
        )

        # Handle API errors
        if response.status_code != 200:
            print(f"Error: {response.status_code}")
            print(response.text)
            break

        data = response.json()

        # Handle GraphQL errors
        if "errors" in data:
            print("GraphQL Errors:")
            for error in data["errors"]:
                print(error["message"])
            break

        # Extract commit history
        history = data["data"]["repository"]["defaultBranchRef"]["target"]["history"]

        # Sum additions and deletions
        for edge in history["edges"]:
            total_additions += edge["node"]["additions"]
            total_deletions += edge["node"]["deletions"]

        # Check for more pages
        has_next_page = history["pageInfo"]["hasNextPage"]
        if has_next_page:
            cursor = history["pageInfo"]["endCursor"]

    return total_additions, total_deletions


def update_contributors_file(contributors_csv, contributors_data):
    """
    Writes updated contributor data back to the CSV file.
    """
    with open(contributors_csv, mode="w", encoding="utf-8", newline="") as contributors_file:
        fieldnames = contributors_data[0].keys()
        writer = csv.DictWriter(contributors_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(contributors_data)


def process_repositories(top_50_repos_csv, base_folder):
    """
    Processes repositories listed in `top_50_repos_csv` and updates the corresponding
    `contributors_details.csv` files with additions and deletions for each contributor.
    """
    with open(top_50_repos_csv, mode="r", encoding="utf-8") as repos_file:
        repos_reader = csv.DictReader(repos_file)
        for repo_row in repos_reader:
            owner = repo_row["Repo Owner"]
            repo = repo_row["Repo Name"]
            contributors_folder = os.path.join(base_folder, f"{owner}_{repo}")
            contributors_csv = os.path.join(contributors_folder, "contributors_details.csv")

            # Skip if contributors file doesn't exist
            if not os.path.exists(contributors_csv):
                print(f"Contributors file not found for {owner}/{repo}")
                continue

            # Read contributors_details.csv
            with open(contributors_csv, mode="r", encoding="utf-8") as contributors_file:
                contributors_reader = csv.DictReader(contributors_file)
                contributors_data = list(contributors_reader)

            # Add new columns if they don't exist
            if "number of additions" not in contributors_data[0]:
                for row in contributors_data:
                    row["number of additions"] = 0
                    row["number of deletions"] = 0

            # Fetch additions and deletions for each contributor
            for row in contributors_data:
                contributor_id = row["Git_Contributor_ID"]
                additions, deletions = fetch_contributor_stats(owner, repo, contributor_id)
                print(f"Contributor: {contributor_id}, Additions: {additions}, Deletions: {deletions}")

                # Update row with new data
                row["number of additions"] = additions
                row["number of deletions"] = deletions

            # Write updated data back to contributors_details.csv
            update_contributors_file(contributors_csv, contributors_data)
            print(f"Updated {owner}/{repo} contributors_details.csv")


# Main execution
if __name__ == "__main__":
    # Path to the top_50_repos.csv file
    TOP_50_REPOS_CSV = "top_50_repos.csv"

    # Base folder containing "repo owner_repo name" folders
    BASE_FOLDER = ""

    # Process repositories
    process_repositories(TOP_50_REPOS_CSV, BASE_FOLDER)