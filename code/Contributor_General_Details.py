import requests
import csv
import os

# GitHub credentials
TOKEN = "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"  # Replace with your GitHub token
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

def analyze_contributor_with_details(contributor_login):
    # Skip bot accounts
    if "[bot]" in contributor_login:
        return {
            "Git_Contributor_ID": "Bot Account",
            "Git_Contributor_Name": contributor_login,
            "Number_of_Commits": 0,
            "Email_ID": "Not Public",
            "Git_Score": 0,
            "Hireable": False,
            "Followers": 0,
            "Type_of_User": "Bot"
        }

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
        __typename
      }
    }
    """
    result = run_graphql_query(query, {"login": contributor_login})
    if not result:
        return {
            "Git_Contributor_ID": "Not Found",
            "Git_Contributor_Name": "Not Found",
            "Number_of_Commits": 0,
            "Email_ID": "Not Public",
            "Git_Score": 0,
            "Hireable": False,
            "Followers": 0,
            "Type_of_User": "Unknown"
        }

    user = result.get('data', {}).get('user', {})
    if user:
        followers_count = user.get('followers', {}).get('totalCount', 0) or 0
        stars_count = user.get('starredRepositories', {}).get('totalCount', 0) or 0
        return {
            "Git_Contributor_ID": user.get('id', "Not Found"),
            "Git_Contributor_Name": user.get('name', "Not Found"),
            "Number_of_Commits": user.get('contributionsCollection', {}).get('totalCommitContributions', 0) or 0,
            "Email_ID": user.get('email', "Not Public"),
            "Git_Score": followers_count + stars_count,
            "Hireable": user.get('isHireable', False),
            "Followers": followers_count,
            "Type_of_User": user.get('__typename', "Unknown")
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
            "Type_of_User": "Unknown"
        }

def save_contributor_details_to_csv(repo_owner, repo_name, contributor_details):
    folder_name = f"{repo_owner}_{repo_name}"
    if not os.path.exists(folder_name):
        try:
            os.makedirs(folder_name)
        except PermissionError:
            print(f"Permission denied: Cannot create folder '{folder_name}'.")
            return

    csv_file_path = os.path.join(folder_name, "contributors_details.csv")

    try:
        file_exists = os.path.isfile(csv_file_path)
        with open(csv_file_path, mode='a', newline='', encoding='utf-8') as file:
            writer = csv.DictWriter(file, fieldnames=contributor_details.keys())
            if not file_exists:
                writer.writeheader()
            writer.writerow(contributor_details)
        print(f"Contributor details saved to {csv_file_path}")
    except PermissionError:
        print(f"Permission denied: Cannot write to file '{csv_file_path}'.")

def get_contributors(owner, repo):
    url = f"https://api.github.com/repos/{owner}/{repo}/contributors"
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

            contributors = get_contributors(repo_owner, repo_name)
            contributors = contributors[:100]  # Limit to 100 contributors

            for contributor in contributors:
                contributor_login = contributor['login']
                print(f"Processing contributor: {contributor_login}")

                contributor_details = analyze_contributor_with_details(contributor_login)
                print("Contributor Details:", contributor_details)

                save_contributor_details_to_csv(repo_owner, repo_name, contributor_details)