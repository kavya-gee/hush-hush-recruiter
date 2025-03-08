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
            # Calculate Git_Score using the new formula
            git_score = (
                (contributor['Number_of_Commits'] * 1000) +  # Commits weight = 1000
                (contributor['number of additions'] * 1) +   # Additions weight = 1
                (contributor['number of deletions'] * 1) +  # Deletions weight = 1
                (contributor['PRs_Created'] * 50) +         # PRs Created weight = 50
                (contributor['PRs_reviewed'] * 150) +        # PRs Reviewed weight = 150
                (contributor['PRs_Merged'] * 100) +          # PRs Merged weight = 100
                (contributor['PRs_Closed'] * 20) +          # PRs Closed weight = 20
                (contributor['Issues_created'] * 10) +       # Issues Created weight = 10
                (contributor['Issues_closed'] * 15) +        # Issues Closed weight = 15
                (contributor['Followers'] * 1)               # Followers weight = 1
            )
            
            # Create a combined row with all required details
            combined_row = {
                'Repo_Name': repo_name,
                'Repo_Owner': repo_owner,
                'Repo_URL': repo['Repo URL'],
                'Stars': repo['Stars'],
                'Forks': repo['Forks'],
                'Number_of_Contributors': repo['Number of Contributors'],
                'Language': repo['Language'],
                'Git_Contributor_ID': contributor['Git_Contributor_ID'],
                'Git_UserName': contributor['Git_UserName'],
                'Git_Contributor_Name': contributor['Git_Contributor_Name'],
                'Number_of_Commits': contributor['Number_of_Commits'],
                'Email_ID': contributor['Email_ID'],
                'Git_Score': git_score,  
                'Hireable': contributor['Hireable'],
                'Followers': contributor['Followers'],
                'Type_of_User': contributor['Type_of_User'],
                'number_of_additions': contributor['number of additions'],
                'number_of_deletions': contributor['number of deletions'],
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

print("Combined CSV file with updated Git_Score created successfully!")