import pickle
import pandas as pd
import numpy as np

# Step 1: Load the Saved Model and Scaler
with open('trained_model.pkl', 'rb') as f:
    model = pickle.load(f)

with open('scaler.pkl', 'rb') as f:
    scaler = pickle.load(f)

# Step 2: Load and Preprocess the Unseen Data
# Load the unseen data
unseen_data = pd.read_csv('Contributors_Details_Part_2.csv')

# Step 2.1: Apply the Same Preprocessing as Training Data
# Fill missing values
columns_to_fill = ['PRs_Created', 'PRs_Merged', 'PRs_Closed', 'Number_of_Commits', 'Stars', 'Forks', 'Followers']
unseen_data[columns_to_fill] = unseen_data[columns_to_fill].fillna(0)

# Step 2.2: Apply Feature Engineering (Same as Training Data)
# Calculate Git_Score
unseen_data['Git_Score'] = (
    unseen_data['Number_of_Commits'].fillna(0) * 1 +
    (unseen_data['PRs_Created'].fillna(0) + unseen_data['PRs_Merged'].fillna(0) + unseen_data['PRs_Closed'].fillna(0)) * 3 +
    unseen_data['Stars'].fillna(0) * 5 +
    unseen_data['Forks'].fillna(0) * 4 +
    unseen_data['Followers'].fillna(0) * 2
)

# Step 2.3: Create Engineered Features (Same as Training Data)
engineered_features_unseen = pd.DataFrame()

# Activity Features
engineered_features_unseen['total_contributions'] = (
    unseen_data['Number_of_Commits'] + unseen_data['PRs_Created'] + unseen_data['PRs_Merged'] + unseen_data['PRs_Closed'] +
    unseen_data['Issues_created'] + unseen_data['Issues_closed']
)

# Efficiency Features
engineered_features_unseen['code_churn'] = unseen_data['number_of_additions'] - unseen_data['number_of_deletions']
engineered_features_unseen['pr_efficiency'] = np.divide(unseen_data['PRs_Merged'], unseen_data['PRs_Created'], where=unseen_data['PRs_Created'] != 0)
engineered_features_unseen['pr_efficiency'] = engineered_features_unseen['pr_efficiency'].fillna(0)

engineered_features_unseen['issue_resolution_rate'] = np.divide(unseen_data['Issues_closed'], unseen_data['Issues_created'], where=unseen_data['Issues_created'] != 0)
engineered_features_unseen['issue_resolution_rate'] = engineered_features_unseen['issue_resolution_rate'].fillna(0)

# Popularity and Influence Features
engineered_features_unseen['repo_popularity_score'] = unseen_data['Stars'] + unseen_data['Forks']
engineered_features_unseen['contributor_influence_score'] = unseen_data['Followers'] * engineered_features_unseen['repo_popularity_score']

# Efficiency Features
engineered_features_unseen['commit_efficiency'] = np.divide(unseen_data['Number_of_Commits'], unseen_data['Number_of_Contributors'], where=unseen_data['Number_of_Contributors'] != 0)
engineered_features_unseen['commit_efficiency'] = engineered_features_unseen['commit_efficiency'].fillna(0)

engineered_features_unseen['addition_efficiency'] = np.divide(unseen_data['number_of_additions'], unseen_data['Number_of_Contributors'], where=unseen_data['Number_of_Contributors'] != 0)
engineered_features_unseen['addition_efficiency'] = engineered_features_unseen['addition_efficiency'].fillna(0)

engineered_features_unseen['deletion_efficiency'] = np.divide(unseen_data['number_of_deletions'], unseen_data['Number_of_Contributors'], where=unseen_data['Number_of_Contributors'] != 0)
engineered_features_unseen['deletion_efficiency'] = engineered_features_unseen['deletion_efficiency'].fillna(0)

# Quality Features
engineered_features_unseen['pr_quality'] = np.divide(unseen_data['PRs_Merged'], unseen_data['PRs_Created'], where=unseen_data['PRs_Created'] != 0)
engineered_features_unseen['pr_quality'] = engineered_features_unseen['pr_quality'].fillna(0)

engineered_features_unseen['issue_quality'] = np.divide(unseen_data['Issues_closed'], unseen_data['Issues_created'], where=unseen_data['Issues_created'] != 0)
engineered_features_unseen['issue_quality'] = engineered_features_unseen['issue_quality'].fillna(0)

# Collaboration Features
engineered_features_unseen['pr_review_participation'] = np.divide(unseen_data['PRs_reviewed'], (unseen_data['PRs_Created'] + unseen_data['PRs_Merged'] + unseen_data['PRs_Closed']), where=(unseen_data['PRs_Created'] + unseen_data['PRs_Merged'] + unseen_data['PRs_Closed']) != 0)
engineered_features_unseen['pr_review_participation'] = engineered_features_unseen['pr_review_participation'].fillna(0)

engineered_features_unseen['collaboration_score'] = unseen_data['PRs_reviewed'] + unseen_data['Issues_closed']

# Add identifier columns (optional)
engineered_features_unseen['Git_Contributor_ID'] = unseen_data['Git_Contributor_ID']
engineered_features_unseen['Git_UserName'] = unseen_data['Git_UserName']
engineered_features_unseen['Repo_Name'] = unseen_data['Repo_Name']
engineered_features_unseen['Repo_Owner'] = unseen_data['Repo_Owner']
engineered_features_unseen['Type_of_User'] = unseen_data['Type_of_User']
engineered_features_unseen['Git_Score'] = unseen_data['Git_Score']
candidate_counts = unseen_data['Git_Contributor_ID'].value_counts()
engineered_features_unseen['candidate_priority'] = unseen_data['Git_Contributor_ID'].map(candidate_counts)
# Step 3: Prepare Data for Prediction
# Drop unnecessary columns (same as during training)
X_unseen = engineered_features_unseen.drop(columns=['Git_Contributor_ID', 'Git_UserName', 'Repo_Name', 'Repo_Owner', 'Type_of_User'])

# Step 4: Normalize the Unseen Data
X_unseen_scaled = scaler.transform(X_unseen)

# Step 5: Make Predictions
# Predict probabilities for the unseen data
engineered_features_unseen['predicted_probability'] = model.predict(X_unseen_scaled)

# If you want binary predictions (0 or 1), you can use a threshold (e.g., 0.5)
engineered_features_unseen['predicted_target'] = (engineered_features_unseen['predicted_probability'] > 0.5).astype(int)

# Step 6: Save the Results
# Save the final results to a CSV file
engineered_features_unseen.to_csv('unseen_data_with_predictions.csv', index=False)

print("Predictions saved to 'unseen_data_with_predictions.csv'.")