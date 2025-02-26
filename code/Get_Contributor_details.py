import requests
import csv
import os

# GitHub credentials
TOKEN = "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"  # Replace with your GitHub token
HEADERS = {"Authorization": f"Bearer {TOKEN}"}
GRAPHQL_URL = "https://api.github.com/graphql"
REST_API_URL = "https://api.github.com"

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
# Function to get merged pull requests authored by a contributor
def get_merged_pull_requests(owner, repo, contributor_login):
    query = """
    query($owner: String!, $repo: String!, $cursor: String) {
        repository(owner: $owner, name: $repo) {
            pullRequests(states: MERGED, first: 100, after: $cursor) {
                edges {
                    node {
                        number
                        title
                        mergedAt
                        author {
                            login
                        }
                    }
                }
                pageInfo {
                    hasNextPage
                    endCursor
                }
            }
        }
    }
    """

    # To handle pagination
    cursor = None
    merged_prs = []

    while True:
        variables = {
            "owner": owner,
            "repo": repo,
            "cursor": cursor
        }

        response = run_graphql_query(query, variables)

        # Ensure the response structure is as expected
        repository = response.get("data", {}).get("repository", {})
        pull_requests = repository.get("pullRequests", {}).get("edges", [])

        for edge in pull_requests:
            node = edge.get('node')
           
            if node:  # Ensure node exists
                author = node.get('author', {})
               
                if author and author.get('login') == contributor_login:
                    merged_at = node.get('mergedAt')
                    merged_at = node.get('mergedAt')
                    if merged_at:
                        merged_prs.append({
                            'number': node.get('number'),
                            'title': node.get('title'),
                            'mergedAt': merged_at,
                            'author': author.get('login')
                        })
       
        # Pagination handling
        page_info = repository.get("pullRequests", {}).get("pageInfo", {})
        if page_info.get("hasNextPage"):
            cursor = page_info.get("endCursor")
        else:
            break

    return merged_prs

# Get the commit history for the default branch of the repositorydef get_commit_history(owner, repo, cursor=None):
def get_commit_history(owner, repo, cursor=None):
    query = """
    query($owner: String!, $repo: String!, $cursor: String) {
      repository(owner: $owner, name: $repo) {
        defaultBranchRef {
          target {
            ... on Commit {
              history(first: 100, after: $cursor) {
                pageInfo {
                  endCursor
                  hasNextPage
                }
                edges {
                  node {
                    committedDate
                    parents(first: 2) {
                      totalCount
                    }
                    author {
                      name
                      user {
                        login
                      }
                    }
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
    all_commits = []
    while True:
        result = run_graphql_query(query, {"owner": owner, "repo": repo, "cursor": cursor})
        if not result:
            print("No result returned from GraphQL query.")
            break

        repository = result.get('data', {}).get('repository', {})
        
        if not repository:
            print("Repository not found in response.")
            break

        default_branch_ref = repository.get('defaultBranchRef', {})
        if not default_branch_ref:
            print("Default branch not found.")
            break

        history = default_branch_ref.get('target', {}).get('history', {})
        commit_nodes = history.get('edges', [])
        
        page_info = history.get('pageInfo', {})

        all_commits.extend(commit_nodes)
        
        if not page_info.get("hasNextPage"):
            print("No more commits to fetch.")
            break
        cursor = page_info.get("endCursor")
        #print(f"Fetching next page with cursor: {cursor}")  # Debugging
        
    return all_commits, page_info
# Analyze contributor with additional details
def analyze_contributor_with_details(owner, contributor_login):
    query = """
    query($login: String!) {
      user(login: $login) {
        id
        name
        email
        isHireable
        followers { totalCount }
        starredRepositories { totalCount }
        contributionsCollection {
          totalCommitContributions
        }
        createdAt
        login
        __typename
      }
    }
    """
    result = run_graphql_query(query, {"login": contributor_login})
    user = result.get('data', {}).get('user', {})

    if user:
        followers_count = user.get('followers', {}).get('totalCount', 0) or 0
        stars_count = user.get('starredRepositories', {}).get('totalCount', 0) or 0
        return {
            "Git_Contributor_ID": user.get('id'),
            "Git_Contributor_Name": user.get('name'),
            "Number_of_Commits": user.get('contributionsCollection', {}).get('totalCommitContributions', 0) or 0,
            "Email_ID": user.get('email') or "Not Public",
            "Git_Score": followers_count + stars_count,
            "Hireable": user.get('isHireable', False),
            "Followers": followers_count,
            "Stars": stars_count,
            "Type_of_User": user.get('__typename')
        }
    else:
        return {
            "Git_Contributor_ID": "Not Found",
            "Git_Contributor_Name": "Not Found",
            "Number_of_Commits": 0,
            "Email_ID": "Not Public",
            "Git_Score": 0,
            "Hireable": False,
            "Followers": 0,
            "Stars": 0,
            "Type_of_User": "Unknown"
        }
# Function to save contributor details to a CSV file
def save_contributor_details_to_csv(repo_owner, repo_name, contributor_details):
    # Create a folder named after the repository
    folder_name = f"{repo_owner}_{repo_name}"
    if not os.path.exists(folder_name):
        os.makedirs(folder_name)

    # Define the CSV file path
    csv_file_path = os.path.join(folder_name, "contributors_details.csv")

    # Write the contributor details to the CSV file
    file_exists = os.path.isfile(csv_file_path)
    with open(csv_file_path, mode='a', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=contributor_details.keys())
        if not file_exists:
            writer.writeheader()
        writer.writerow(contributor_details)

    print(f"Contributor details saved to {csv_file_path}")
# Function to get contributors from a repository using REST API
def get_contributors(owner, repo):
    url = f"{REST_API_URL}/repos/{owner}/{repo}/contributors"
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    contributors = response.json()
    return contributors
if __name__ == "__main__":
    with open('top_50_repos.csv', mode='r', encoding='utf-8') as csv_file:
        csv_reader = csv.DictReader(csv_file)
        for row in csv_reader:
            repo_owner = row['Repo Owner']
            repo_name = row['Repo Name']
            

            # Fetch contributors for the repository
            contributors = get_contributors(repo_owner, repo_name)

            

            # Limit to 100 contributors
            contributors = contributors[:100]

            # Fetch all commits for the repository
            all_commits, page_info = get_commit_history(repo_owner, repo_name)

            print(f"Total commits fetched: {len(all_commits)}")

            for contributor in contributors:
                contributor_login = contributor['login']
                print(f"Processing contributor: {contributor_login}")

                # Fetch contributor details
                contributor_details = analyze_contributor_with_details(repo_owner, contributor_login)
                print("Contributor Details:", contributor_details)

                if not contributor_details:
                    print(f"No details found for contributor: {contributor_login}")
                    continue

                # Filter commits by contributor
                contributor_commits = [
                    commit for commit in all_commits
                    if commit['node']['author']['user'] and commit['node']['author']['user']['login'] == contributor_login
                ]

                total_commits = len(contributor_commits)
                total_additions = sum(c['node'].get('additions', 0) for c in contributor_commits)
                total_deletions = sum(c['node'].get('deletions', 0) for c in contributor_commits)

                # Fetch merged PRs for the contributor
                merged_prs = get_merged_pull_requests(repo_owner, repo_name, contributor_login)
                merged_pr_count = len(merged_prs)

                # Update the contributor details with commits and merged PRs
                contributor_details.update({
                    "Number_of_Commits": total_commits,
                    "Number_of_Additions": total_additions,
                    "Number_of_Deletions": total_deletions,
                    "Merged_PRs": merged_pr_count
                })

                # Print the final details
                print(f"Final Contributor Metrics with Additional Details for {repo_owner}/{repo_name} (Contributor: {contributor_login}):\n{contributor_details}")
                
                # Save contributor details to a CSV file
                save_contributor_details_to_csv(repo_owner, repo_name, contributor_details)