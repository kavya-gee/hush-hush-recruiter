import requests
import csv
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from collections import defaultdict

# Configuration
GITHUB_API_URL = "https://api.github.com/graphql"
GITHUB_TOKEN = "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"
HEADERS = {"Authorization": f"Bearer {GITHUB_TOKEN}", "Content-Type": "application/json"}
MAX_WORKERS = 2
PRINT_LOCK = Lock()

# GraphQL Query (Focused on Reviews)
GRAPHQL_QUERY = """
query ($owner: String!, $name: String!, $cursor: String) {
  repository(owner: $owner, name: $name) {
    pullRequests(
      first: 100
      after: $cursor
      orderBy: { field: CREATED_AT, direction: DESC }
    ) {
      edges {
        node {
          id  # Unique PR identifier
          reviews(first: 100) {
            edges {
              node {
                author {
                  ... on User {
                    id
                  }
                }
              }
            }
          }
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
    """Read repositories from CSV without modifying existing data"""
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

def fetch_all_reviews(owner, repo):
    """Fetch all PR reviews while preserving existing columns"""
    all_reviews = []
    cursor = None

    while True:
        variables = {"owner": owner, "name": repo}
        if cursor: variables["cursor"] = cursor
        
        try:
            response = requests.post(
                GITHUB_API_URL,
                json={"query": GRAPHQL_QUERY, "variables": variables},
                headers=HEADERS,
                timeout=30
            )
            response.raise_for_status()
            data = response.json()

            if "errors" in data:
                with PRINT_LOCK:
                    print(f"Error for {owner}/{repo}: {data['errors']}")
                break

            # Collect reviews without affecting other columns
            pr_edges = data["data"]["repository"]["pullRequests"]["edges"]
            for pr_edge in pr_edges:
                pr_id = pr_edge["node"]["id"]
                reviews = pr_edge["node"]["reviews"]["edges"]
                all_reviews.extend([(pr_id, review) for review in reviews])

            page_info = data["data"]["repository"]["pullRequests"]["pageInfo"]
            if page_info["hasNextPage"]:
                cursor = page_info["endCursor"]
                time.sleep(1)
            else:
                break

        except Exception as e:
            with PRINT_LOCK:
                print(f"API Error for {owner}/{repo}: {str(e)}")
            break

    return all_reviews

def process_repository(owner, repo):
    """Add review column while keeping existing data intact"""
    folder = f"{owner}_{repo}"
    csv_path = os.path.join(folder, "contributors_details.csv")
    
    if not os.path.exists(csv_path):
        return

    # Get review data without modifying existing stats
    reviews = fetch_all_reviews(owner, repo)
    
    # Track unique PR reviews per contributor
    reviewer_stats = defaultdict(set)
    for pr_id, review in reviews:
        reviewer = review["node"]["author"]
        if reviewer and reviewer.get("id"):
            reviewer_id = reviewer["id"]
            reviewer_stats[reviewer_id].add(pr_id)

    # Read existing CSV data
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        original_columns = reader.fieldnames

    # Add new column to existing data
    NEW_COLUMN = "PRs_reviewed"
    for row in rows:
        # Preserve all existing values
        existing_values = {k: v for k, v in row.items()}
        
        # Calculate new value
        contributor_id = row.get("Git_Contributor_ID")
        if not contributor_id or row.get("Type_of_L") == "Bot":
            existing_values[NEW_COLUMN] = 0
        else:
            existing_values[NEW_COLUMN] = len(reviewer_stats.get(contributor_id, set()))
        
        row.update(existing_values)

    # Write back with original + new column
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        # Preserve original column order + append new column
        fieldnames = original_columns.copy()
        if NEW_COLUMN not in fieldnames:
            fieldnames.append(NEW_COLUMN)
        
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    with PRINT_LOCK:
        print(f"✅ Updated {owner}/{repo} (Added column: {NEW_COLUMN})")

def main():
    """Main executor preserving all existing data"""
    repos = read_repos_from_csv()
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(process_repository, owner, repo): (owner, repo) for owner, repo in repos}
        for future in as_completed(futures):
            owner, repo = futures[future]
            try:
                future.result()
            except Exception as e:
                with PRINT_LOCK:
                    print(f"❌ Failed {owner}/{repo}: {str(e)}")

if __name__ == "__main__":
    start_time = time.time()
    main()
    print(f"⏱️ Total time: {time.time() - start_time:.2f}s")