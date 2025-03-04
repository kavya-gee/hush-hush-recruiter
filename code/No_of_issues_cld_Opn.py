import requests
import csv
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

# Configuration
GITHUB_API_URL = "https://api.github.com/graphql"
GITHUB_TOKEN = "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"  # Replace with your token
HEADERS = {"Authorization": f"Bearer {GITHUB_TOKEN}", "Content-Type": "application/json"}
MAX_WORKERS = 3  # Number of threads for concurrent pro cessing
PRINT_LOCK = Lock()  # Lock for thread-safe printing

# GraphQL Query for Issues
GRAPHQL_QUERY_ISSUES = """
query ($owner: String!, $name: String!, $cursor: String) {
  repository(owner: $owner, name: $name) {
    issues(
      first: 100
      after: $cursor
      states: [OPEN, CLOSED]  # Fetch both open and closed issues
      orderBy: { field: CREATED_AT, direction: DESC }
    ) {
      edges {
        node {
          author {
            ... on User {
              id
            }
          }
          state
        }
      }
      pageInfo {
        endCursor
        hasNextPage
      }
    }
  }
}
"""

def read_repos_from_csv():
    """Read repositories from top_50_repos.csv."""
    repos = []
    try:
        with open("top_50_repos.csv", "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                repos.append((row["Repo Owner"].strip(), row["Repo Name"].strip()))
    except Exception as e:
        with PRINT_LOCK:
            print(f"Error reading repos: {str(e)}")
    return repos

def fetch_all_issues(owner, repo):
    """Fetch all issues for a repository using pagination."""
    issues = []
    cursor = None
    has_next_page = True

    while has_next_page:
        variables = {"owner": owner, "name": repo}
        if cursor:
            variables["cursor"] = cursor

        response = requests.post(
            GITHUB_API_URL,
            json={"query": GRAPHQL_QUERY_ISSUES, "variables": variables},
            headers=HEADERS,
            timeout=20
        )
        response.raise_for_status()
        data = response.json()

        if "errors" in data:
            with PRINT_LOCK:
                print(f"Error for {owner}/{repo}: {data['errors']}")
            break

        # Append issues to the list
        issues.extend(data["data"]["repository"]["issues"]["edges"])

        # Update pagination cursor
        page_info = data["data"]["repository"]["issues"]["pageInfo"]
        has_next_page = page_info["hasNextPage"]
        cursor = page_info["endCursor"]

        # Add a delay to avoid hitting the rate limit
        time.sleep(1)

    return issues

def count_issues_by_contributor(issues):
    """Count the number of issues created and closed by each contributor."""
    contributor_stats = {}

    for edge in issues:
        node = edge["node"]
        author = node["author"]
        state = node["state"]

        if author and author.get("id"):
            contributor_id = author["id"]

            if contributor_id not in contributor_stats:
                contributor_stats[contributor_id] = {"Issues_created": 0, "Issues_closed": 0}

            # Count issues created
            contributor_stats[contributor_id]["Issues_created"] += 1

            # Count issues closed
            if state == "CLOSED":
                contributor_stats[contributor_id]["Issues_closed"] += 1

    return contributor_stats

def update_contributor_details(owner, repo, contributor_stats):
    """Update contributors_details.csv with Issues_created and Issues_closed."""
    folder = f"{owner}_{repo}"
    csv_path = os.path.join(folder, "contributors_details.csv")

    if not os.path.exists(csv_path):
        with PRINT_LOCK:
            print(f"File not found: {csv_path}")
        return

    # Read existing contributor details
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = reader.fieldnames

    # Add new columns if they don't exist
    if "Issues_created" not in fieldnames:
        fieldnames.append("Issues_created")
    if "Issues_closed" not in fieldnames:
        fieldnames.append("Issues_closed")

    # Update rows with issues data
    for row in rows:
        contributor_id = row["Git_Contributor_ID"]
        if contributor_id in contributor_stats:
            row["Issues_created"] = contributor_stats[contributor_id]["Issues_created"]
            row["Issues_closed"] = contributor_stats[contributor_id]["Issues_closed"]
        else:
            row["Issues_created"] = 0
            row["Issues_closed"] = 0

    # Write updated data back to CSV
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    with PRINT_LOCK:
        print(f"Updated {csv_path} with Issues_created and Issues_closed data")

def process_repository(owner, repo):
    """Process a single repository to fetch issues and update contributor details."""
    with PRINT_LOCK:
        print(f"Processing {owner}/{repo}...")

    # Fetch all issues for the repository
    issues = fetch_all_issues(owner, repo)

    # Count issues created and closed by contributor
    contributor_stats = count_issues_by_contributor(issues)

    # Update contributors_details.csv with issues data
    update_contributor_details(owner, repo, contributor_stats)

    with PRINT_LOCK:
        print(f"Completed {owner}/{repo}")

def main():
    """Main function to process repositories with threading."""
    repos = read_repos_from_csv()

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # Submit all repositories for processing
        futures = {executor.submit(process_repository, owner, repo): (owner, repo) for owner, repo in repos}

        # Monitor progress
        for future in as_completed(futures):
            owner, repo = futures[future]
            try:
                future.result()
            except Exception as e:
                with PRINT_LOCK:
                    print(f"Error processing {owner}/{repo}: {str(e)}")

    print("Done!")

if __name__ == "__main__":
    start_time = time.time()
    main()
    print(f"⏱️ Total execution time: {time.time() - start_time:.2f} seconds")