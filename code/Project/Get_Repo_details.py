import requests
import csv
import time

# GitHub credentials (use environment variables for security)
TOKEN = "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"  # Replace with your token
HEADERS = {"Authorization": f"Bearer {TOKEN}"}
GRAPHQL_URL = "https://api.github.com/graphql"

# Add a delay between requests (in seconds)
REQUEST_DELAY = 1  # Adjust as needed

# Run GraphQL Query
def run_graphql_query(query, variables):
    try:
        response = requests.post(
            GRAPHQL_URL,
            json={"query": query, "variables": variables},
            headers=HEADERS
        )
        response.raise_for_status()
        data = response.json()

        # Check rate limit
        rate_limit_remaining = int(response.headers.get('X-RateLimit-Remaining', 0))
        print(f"Rate Limit Remaining: {rate_limit_remaining}")
        if rate_limit_remaining == 0:
            print("Rate limit exceeded. Please wait before making more requests.")
            return None

        if 'errors' in data:
            print("GraphQL Errors:", data['errors'])
        return data
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        return None

# Function to get the number of contributors
def get_number_of_contributors(owner, repo):
    contributors_url = f"https://api.github.com/repos/{owner}/{repo}/contributors?per_page=100"
    contributors_count = 0
    print(f"Fetching contributors for {owner}/{repo}")
    while contributors_url:
        try:
            response = requests.get(contributors_url, headers=HEADERS)
            response.raise_for_status()
            contributors = response.json()
            contributors_count += len(contributors)
            contributors_url = response.links.get('next', {}).get('url')
            time.sleep(REQUEST_DELAY)  # Add delay to avoid rate limiting
        except requests.exceptions.RequestException as e:
            print(f"Failed to fetch contributors for {owner}/{repo}: {e}")
            return 0
    return contributors_count

# Function to get pull requests (open or closed)
def get_pull_requests(owner, repo, state):
    print(f"Fetching {state} PRs for {owner}/{repo}")
    query = """
    query($owner: String!, $repo: String!, $state: [PullRequestState!], $cursor: String) {
        repository(owner: $owner, name: $repo) {
            pullRequests(states: $state, first: 100, after: $cursor) {
                edges {
                    node {
                        number
                        title
                    }
                }
                pageInfo {
                    hasNextPage
                    endCursor
                }
            }
            issues(states: OPEN) {
                totalCount
            }
        }
    }
    """
    cursor = None
    prs = []
    total_closed_issues = 0  # Track the total number of closed issues

    while True:
        variables = {
            "owner": owner,
            "repo": repo,
            "state": [state.upper()],  # Pass state as a list
            "cursor": cursor
        }

        response = run_graphql_query(query, variables)
        if not response:
            print(f"No response received for {owner}/{repo}. Breaking loop.")
            break

        repository = response.get("data", {}).get("repository", {})
        if not repository:
            print(f"No repository data found for {owner}/{repo}. Breaking loop.")
            break

        # Fetch open issues count
        open_issues = repository.get("issues", {}).get("totalCount", 0)
        print(f"Found {open_issues} open issues for {owner}/{repo}")

        # Fetch pull requests
        pull_requests = repository.get("pullRequests", {}).get("edges", [])
        print(f"Found {len(pull_requests)} {state} PRs for {owner}/{repo}")

        for edge in pull_requests:
            node = edge.get('node')
            if node:
                prs.append({
                    'number': node.get('number'),
                    'title': node.get('title')
                })

        # Update the total count of closed issues
        if state.upper() == "CLOSED":
            total_closed_issues += len(pull_requests)
            print(f"Total closed issues so far: {total_closed_issues}")

            # If closed issues exceed 100, break the loop
            if total_closed_issues > 100:
                print(f"More than 100 closed issues found for {owner}/{repo}. Breaking loop.")
                break

        page_info = repository.get("pullRequests", {}).get("pageInfo", {})
        if page_info.get("hasNextPage"):
            cursor = page_info.get("endCursor")
            print(f"Fetching next page of PRs for {owner}/{repo} with cursor: {cursor}")
            time.sleep(REQUEST_DELAY)  # Add delay to avoid rate limiting
        else:
            print(f"No more PRs to fetch for {owner}/{repo}.")
            break

    # Return the number of open issues and closed issues
    if state.upper() == "OPEN":
        return len(prs), open_issues
    elif state.upper() == "CLOSED":
        if total_closed_issues > 100:
            return "More than 100 closed issues", open_issues
        else:
            return len(prs), open_issues

# Function to get repository details
def get_repository_details():
    query = """
    query {
        search(query: "stars:>0", type: REPOSITORY, first: 50) {
            edges {
                node {
                    ... on Repository {
                        name
                        owner {
                            login
                        }
                        url
                        stargazerCount
                        forkCount
                        issues(states: OPEN) {
                            totalCount
                        }
                        languages(first: 1) {
                            edges {
                                node {
                                    name
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    """
    repos = []

    # Run the query once (no pagination needed)
    result = run_graphql_query(query, variables={})
    if not result:
        print("No result returned from GraphQL query.")
        return repos

    search_data = result.get('data', {}).get('search', {})
    edges = search_data.get('edges', [])
    print(f"Number of edges (repositories) found: {len(edges)}")

    for i, edge in enumerate(edges):
        try:
            print(f"\nProcessing repository {i + 1} of {len(edges)}")
            repo = edge.get('node', {})
            print(f"Repository Node: {repo}")

            name = repo.get('name')
            owner = repo.get('owner', {}).get('login')
            url = repo.get('url')
            stars = repo.get('stargazerCount')
            forks = repo.get('forkCount')
            open_issues = repo.get('issues', {}).get('totalCount', 0)

            languages = repo.get('languages', {}).get('edges', [])
            language = languages[0].get('node', {}).get('name', 'Unknown') if languages else 'Unknown'

            # Fetch additional details (with error handling)
            print(f"Fetching details for {owner}/{name}")

            # Fetch contributors
            try:
                num_contributors = get_number_of_contributors(owner, name)
                if num_contributors is None:
                    num_contributors = 0  # Default value
            except Exception as e:
                print(f"Error fetching contributors for {owner}/{name}: {e}")
                num_contributors = 0

            # Fetch pull requests
            try:
                open_prs, open_issues = get_pull_requests(owner, name, "OPEN")
            except Exception as e:
                print(f"Error fetching open PRs for {owner}/{name}: {e}")
                open_prs, open_issues = 0, 0

            try:
                closed_prs, open_issues = get_pull_requests(owner, name, "CLOSED")
            except Exception as e:
                print(f"Error fetching closed PRs for {owner}/{name}: {e}")
                closed_prs, open_issues = 0, 0

            # Append repository details to the list
            repos.append({
                'Repo_Name': name,
                'Repo_Owner': owner,
                'Repo_URL': url,
                'Stars': stars,
                'Forks': forks,
                'Number_of_Contributors': num_contributors,
                'Pull_Requests_Open': open_prs,
                'Pull_Requests_Closed': closed_prs,
                'Open_Issues': open_issues,
                'Language': language
            })

        except Exception as e:
            print(f"Error processing repository {i + 1}: {e}")

    print(f"\nTotal repositories processed: {len(repos)}")
    for repo in repos:
        print(repo)

    return repos

# Write data to CSV
def write_repos_to_csv(repos, filename='top_50_repos.csv'):
    if not repos:
        print("No data to write to CSV.")
        return

    with open(filename, mode='w', newline='', encoding='utf-8') as file:
        fieldnames = repos[0].keys()
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for repo in repos:
            writer.writerow(repo)

if __name__ == "__main__":
    # Get repository details
    repos = get_repository_details()

    if not repos:
        print("No repositories found. Exiting.")
        exit()

    # Write the details to CSV
    write_repos_to_csv(repos, filename='top_50_repos.csv')

    print("Top 50 repositories details written to 'top_50_repos.csv'.")