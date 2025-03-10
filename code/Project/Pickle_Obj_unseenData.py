import pickle
import pandas as pd
import numpy as np

# Step 1: Load the Model and Scaler
with open('trained_model.pkl', 'rb') as f:
    model = pickle.load(f)

with open('scaler.pkl', 'rb') as f:
    scaler = pickle.load(f)

# Step 2: Load and Preprocess the New Dataset
new_data = pd.read_csv('Contributors_Details_Part_5.csv')  # Replace with your new dataset file path

# Perform the same feature engineering as before
engineered_features_new = pd.DataFrame()

# Activity Features
engineered_features_new['total_contributions'] = (
    new_data['Number_of_Commits'] + new_data['PRs_Created'] + new_data['PRs_Merged'] + new_data['PRs_Closed'] +
    new_data['Issues_created'] + new_data['Issues_closed']
)

# Efficiency Features
engineered_features_new['code_churn'] = np.abs(new_data['number_of_additions'] - new_data['number_of_deletions'])
engineered_features_new['pr_efficiency'] = np.divide(new_data['PRs_Merged'], new_data['PRs_Created'], where=new_data['PRs_Created'] != 0)
engineered_features_new['pr_efficiency'] = engineered_features_new['pr_efficiency'].fillna(0)

engineered_features_new['issue_resolution_rate'] = np.divide(new_data['Issues_closed'], new_data['Issues_created'], where=new_data['Issues_created'] != 0)
engineered_features_new['issue_resolution_rate'] = engineered_features_new['issue_resolution_rate'].fillna(0)

# Popularity and Influence Features
engineered_features_new['repo_popularity_score'] = new_data['Stars'] + new_data['Forks']
engineered_features_new['contributor_influence_score'] = new_data['Followers'] * engineered_features_new['repo_popularity_score']

# Efficiency Features
engineered_features_new['commit_efficiency'] = np.divide(new_data['Number_of_Commits'], new_data['Number_of_Contributors'], where=new_data['Number_of_Contributors'] != 0)
engineered_features_new['commit_efficiency'] = engineered_features_new['commit_efficiency'].fillna(0)

engineered_features_new['addition_efficiency'] = np.divide(new_data['number_of_additions'], new_data['Number_of_Contributors'], where=new_data['Number_of_Contributors'] != 0)
engineered_features_new['addition_efficiency'] = engineered_features_new['addition_efficiency'].fillna(0)

engineered_features_new['deletion_efficiency'] = np.divide(new_data['number_of_deletions'], new_data['Number_of_Contributors'], where=new_data['Number_of_Contributors'] != 0)
engineered_features_new['deletion_efficiency'] = engineered_features_new['deletion_efficiency'].fillna(0)

# Quality Features
engineered_features_new['pr_quality'] = np.divide(new_data['PRs_Merged'], new_data['PRs_Created'], where=new_data['PRs_Created'] != 0)
engineered_features_new['pr_quality'] = engineered_features_new['pr_quality'].fillna(0)

engineered_features_new['issue_quality'] = np.divide(new_data['Issues_closed'], new_data['Issues_created'], where=new_data['Issues_created'] != 0)
engineered_features_new['issue_quality'] = engineered_features_new['issue_quality'].fillna(0)

# Collaboration Features
engineered_features_new['pr_review_participation'] = np.divide(new_data['PRs_reviewed'], (new_data['PRs_Created'] + new_data['PRs_Merged'] + new_data['PRs_Closed']), where=(new_data['PRs_Created'] + new_data['PRs_Merged'] + new_data['PRs_Closed']) != 0)
engineered_features_new['pr_review_participation'] = engineered_features_new['pr_review_participation'].fillna(0)

engineered_features_new['collaboration_score'] = new_data['PRs_reviewed'] + new_data['Issues_closed']

# Add identifier columns
engineered_features_new['Git_Contributor_ID'] = new_data['Git_Contributor_ID']
engineered_features_new['Git_UserName'] = new_data['Git_UserName']
engineered_features_new['Repo_Name'] = new_data['Repo_Name']
engineered_features_new['Repo_Owner'] = new_data['Repo_Owner']
engineered_features_new['Type_of_User'] = new_data['Type_of_User']

# Filter rows where Type_of_User == "User"
engineered_features_new = engineered_features_new[engineered_features_new['Type_of_User'] == 'User']

# Prioritize repeated candidates
candidate_counts = engineered_features_new['Git_Contributor_ID'].value_counts()
engineered_features_new['candidate_priority'] = engineered_features_new['Git_Contributor_ID'].map(candidate_counts)

# Drop identifier columns and categorical features for prediction
X_new = engineered_features_new.drop(columns=['Git_Contributor_ID', 'Git_UserName', 'Repo_Name', 'Repo_Owner', 'Type_of_User'])

# Normalize the features using the loaded scaler
X_new_scaled = scaler.transform(X_new)

# Step 3: Make Predictions
engineered_features_new['predicted_probability'] = model.predict(X_new_scaled)

# Step 4: Rank Candidates
# Define weights for each factor
weight_predicted_probability = 0.6
weight_candidate_priority = 0.4

# Calculate combined score
engineered_features_new['combined_score'] = (
    (weight_predicted_probability * engineered_features_new['predicted_probability']) +
    (weight_candidate_priority * engineered_features_new['candidate_priority'])
)

# Rank candidates within each repository based on the combined score
engineered_features_new['rank_in_repo'] = engineered_features_new.groupby('Repo_Name')['combined_score'].rank(ascending=True)

# Select top 5 candidates per repository
top_5_per_repo_new = engineered_features_new[engineered_features_new['rank_in_repo'] <= 5]

# Aggregate top 5 candidates from all repositories
aggregated_candidates_new = top_5_per_repo_new.groupby('Git_Contributor_ID').agg({
    'combined_score': 'max',  # Average combined score across repositories
    'candidate_priority': 'max',  # Maximum priority (number of repositories)
    'Git_UserName': 'first',  # Keep the first occurrence of Git_UserName
}).reset_index()

# Rank candidates globally based on combined score and priority
aggregated_candidates_new['global_rank'] = aggregated_candidates_new.sort_values(
    by=['combined_score', 'candidate_priority'], ascending=[True, True]
).reset_index(drop=True).index + 1

# Select top 50 candidates globally
top_50_candidates_new = aggregated_candidates_new[aggregated_candidates_new['global_rank'] <= 50]

# Display the final top 50 candidates
print(top_50_candidates_new[['Git_Contributor_ID', 'Git_UserName', 'combined_score', 'candidate_priority', 'global_rank']])

# Save the final results to a CSV file
top_50_candidates_new.to_csv('top_50_candidates_new.csv', index=False)