import os
import pandas as pd

# Load the top 50 repositories CSV file
top_50_repos = pd.read_csv('top_50_repos.csv')

# Initialize an empty list to store the combined data
combined_data = []

# Iterate through each repository in the top 50 repos
for index, repo in top_50_repos.iterrows():
    repo_name = repo['Repo Name']
    repo_owner = repo['Repo Owner']
    
    # Construct the path to the contributors_details.csv file
    contributors_file_path = os.path.join(repo_owner + '_' + repo_name, 'contributors_details.csv')
    
    # Check if the contributors_details.csv file exists
    if os.path.exists(contributors_file_path):
        # Load the contributors_details.csv file
        contributors_details = pd.read_csv(contributors_file_path)
        
        # Merge the repository details with the contributor details
        for _, contributor in contributors_details.iterrows():
            # Calculate Git_Score using the provided formula
            git_score = (
                (contributor['Number_of_Commits'] * 1) +
                ((contributor['PRs_Created'] + contributor['PRs_Merged'] + contributor['PRs_Closed']) * 3) +
                (repo['Stars'] * 5) +
                (repo['Forks'] * 4) +
                (contributor['Followers'] * 2)
            )
            
            # Create a combined row with all required details
            combined_row = {
                'Repo Name': repo_name,
                'Repo Owner': repo_owner,
                'Repo URL': repo['Repo URL'],
                'Stars': repo['Stars'],
                'Forks': repo['Forks'],
                'Number of Contributors': repo['Number of Contributors'],
                'Language': repo['Language'],
                'Git_Contributor_ID': contributor['Git_Contributor_ID'],
                'Git_Contributor_Name': contributor['Git_Contributor_Name'],
                'Number_of_Commits': contributor['Number_of_Commits'],
                'Email_ID': contributor['Email_ID'],
                'Git_Score': git_score,  
                'Hireable': contributor['Hireable'],
                'Followers': contributor['Followers'],
                'Type_of_User': contributor['Type_of_User'],
                'number of additions': contributor['number of additions'],
                'number of deletions': contributor['number of deletions'],
                'PRs_Created': contributor['PRs_Created'],
                'PRs_Merged': contributor['PRs_Merged'],
                'PRs_Closed': contributor['PRs_Closed'],
                'PRs_reviewed': contributor['PRs_reviewed'],
                'Issues_created': contributor['Issues_created'],
                'Issues_closed': contributor['Issues_closed']
            }
            
            # Append the combined row to the list
            combined_data.append(combined_row)

# Convert the combined data list to a DataFrame
combined_df = pd.DataFrame(combined_data)

# Write the combined DataFrame to a new CSV file
combined_df.to_csv('Contributors_Details_Final.csv', index=False)

print("Combined CSV file with Git_Score created successfully!")