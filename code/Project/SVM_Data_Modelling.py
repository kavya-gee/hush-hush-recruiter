import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from sklearn.metrics import accuracy_score
import pickle

# Step 1: Read the CSV file into a DataFrame
df = pd.read_csv('Contributors_Details_Final.csv')

# Step 2: Replace blank values with 0 in the specified columns
columns_to_fill = ['PRs_Created', 'PRs_Merged', 'PRs_Closed']
df[columns_to_fill] = df[columns_to_fill].fillna(0)

# Step 3: Calculate Git_Score
df['Git_Score'] = (
    (df['Number_of_Commits'].fillna(0) * 1000) +  # Commits weight = 1000
    (df['number_of_additions'].fillna(0) * 1) +   # Additions weight = 1
    (df['number_of_deletions'].fillna(0) * 1) +  # Deletions weight = 1
    (df['PRs_Created'].fillna(0) * 50) +         # PRs Created weight = 50
    (df['PRs_reviewed'].fillna(0) * 150) +        # PRs Reviewed weight = 150
    (df['PRs_Merged'].fillna(0) * 100) +          # PRs Merged weight = 100
    (df['PRs_Closed'].fillna(0) * 20) +          # PRs Closed weight = 20
    (df['Issues_created'].fillna(0) * 10) +       # Issues Created weight = 10
    (df['Issues_closed'].fillna(0) * 15) +        # Issues Closed weight = 15
    (df['Followers'].fillna(0) * 1)               # Followers weight = 1
)

# Step 4: Feature Engineering
engineered_features = pd.DataFrame()

# Activity Features
engineered_features['total_contributions'] = (
    df['Number_of_Commits'] + df['PRs_Created'] + df['PRs_Merged'] + df['PRs_Closed'] +
    df['Issues_created'] + df['Issues_closed']
)

# Efficiency Features
engineered_features['code_churn'] = np.abs(df['number_of_additions'] - df['number_of_deletions'])

engineered_features['pr_efficiency'] = np.divide(df['PRs_Merged'], df['PRs_Created'], where=df['PRs_Created'] != 0)
engineered_features['pr_efficiency'] = engineered_features['pr_efficiency'].fillna(0)

engineered_features['issue_resolution_rate'] = np.divide(df['Issues_closed'], df['Issues_created'], where=df['Issues_created'] != 0)
engineered_features['issue_resolution_rate'] = engineered_features['issue_resolution_rate'].fillna(0)

# Popularity and Influence Features
engineered_features['repo_popularity_score'] = df['Stars'] + df['Forks']
engineered_features['contributor_influence_score'] = df['Followers'] * engineered_features['repo_popularity_score']

# Efficiency Features (Contributor-Level)
engineered_features['commit_efficiency'] = np.divide(df['Number_of_Commits'], df['Number_of_Contributors'], where=df['Number_of_Contributors'] != 0)
engineered_features['commit_efficiency'] = engineered_features['commit_efficiency'].fillna(0)

engineered_features['addition_efficiency'] = np.divide(df['number_of_additions'], df['Number_of_Contributors'], where=df['Number_of_Contributors'] != 0)
engineered_features['addition_efficiency'] = engineered_features['addition_efficiency'].fillna(0)

engineered_features['deletion_efficiency'] = np.divide(df['number_of_deletions'], df['Number_of_Contributors'], where=df['Number_of_Contributors'] != 0)
engineered_features['deletion_efficiency'] = engineered_features['deletion_efficiency'].fillna(0)

# Quality Features
engineered_features['pr_quality'] = np.divide(df['PRs_Merged'], df['PRs_Created'], where=df['PRs_Created'] != 0)
engineered_features['pr_quality'] = engineered_features['pr_quality'].fillna(0)

engineered_features['issue_quality'] = np.divide(df['Issues_closed'], df['Issues_created'], where=df['Issues_created'] != 0)
engineered_features['issue_quality'] = engineered_features['issue_quality'].fillna(0)

# Collaboration Features
engineered_features['pr_review_participation'] = np.divide(df['PRs_reviewed'], (df['PRs_Created'] + df['PRs_Merged'] + df['PRs_Closed']), where=(df['PRs_Created'] + df['PRs_Merged'] + df['PRs_Closed']) != 0)
engineered_features['pr_review_participation'] = engineered_features['pr_review_participation'].fillna(0)

engineered_features['collaboration_score'] = df['PRs_reviewed'] + df['Issues_closed']

# Target Column
git_score_threshold = 95000
engineered_features['target'] = (df['Git_Score'] > git_score_threshold).astype(int)

# Add identifier columns
engineered_features['Git_Contributor_ID'] = df['Git_Contributor_ID']
engineered_features['Git_UserName'] = df['Git_UserName']
engineered_features['Repo_Name'] = df['Repo_Name']
engineered_features['Repo_Owner'] = df['Repo_Name']
engineered_features['Type_of_User'] = df['Type_of_User']
engineered_features['Git_Score'] = df['Git_Score']

# Step 5: Preprocess the Data
# Filter rows where Type_of_User == "User"
engineered_features = engineered_features[engineered_features['Type_of_User'] == 'User']

# Prioritize repeated candidates
candidate_counts = engineered_features['Git_Contributor_ID'].value_counts()
engineered_features['candidate_priority'] = engineered_features['Git_Contributor_ID'].map(candidate_counts)

# Separate features and target
X = engineered_features.drop(columns=['target', 'Git_Contributor_ID', 'Git_UserName', 'Repo_Name', 'Repo_Owner', 'Type_of_User'])
y = engineered_features['target']

# Split the data into training and testing sets
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Normalize numerical features
scaler = StandardScaler()
X_train = scaler.fit_transform(X_train)
X_test = scaler.transform(X_test)

# Step 6: Train the SVM Model
# Define the SVM model
svm_model = SVC(kernel='rbf', probability=True, random_state=42)

# Train the model
svm_model.fit(X_train, y_train)

# Evaluate the model
y_pred = svm_model.predict(X_test)
accuracy = accuracy_score(y_test, y_pred)
print(f"Test Accuracy: {accuracy:.4f}")

# Save the model and scaler to files
with open('trained_svm_model.pkl', 'wb') as f:
    pickle.dump(svm_model, f)

with open('scaler.pkl', 'wb') as f:
    pickle.dump(scaler, f)

# Step 7: Apply Ranking Logic
# Predict probabilities for all candidates
engineered_features['predicted_probability'] = svm_model.predict_proba(scaler.transform(
    engineered_features.drop(columns=['target', 'Git_Contributor_ID', 'Git_UserName', 'Repo_Name', 'Repo_Owner', 'Type_of_User'])
))[:, 1]

# Define weights for each factor
weight_predicted_probability = 0.6
weight_git_score = 0.2
weight_candidate_priority = 0.1

# Calculate combined score
engineered_features['combined_score'] = (
    (weight_predicted_probability * engineered_features['predicted_probability']) +
    (weight_git_score * engineered_features['Git_Score']) +
    (weight_candidate_priority * engineered_features['candidate_priority'])
)

# Rank candidates within each repository based on the combined score
engineered_features['rank_in_repo'] = engineered_features.groupby('Repo_Name')['combined_score'].rank(ascending=False)

# Select top 5 candidates per repository
top_5_per_repo = engineered_features[engineered_features['rank_in_repo'] <= 5]

# Step 8: Aggregate and Prioritize Repeated Candidates
# Aggregate top 5 candidates from all repositories
aggregated_candidates = top_5_per_repo.groupby('Git_Contributor_ID').agg({
    'combined_score': 'mean',  # Average combined score across repositories
    'candidate_priority': 'max',  # Maximum priority (number of repositories)
    'Git_UserName': 'first',  # Keep the first occurrence of Git_UserName
    'target': 'first'  # Keep the first occurrence of target
}).reset_index()

# Rank candidates globally based on combined score and priority
aggregated_candidates['global_rank'] = aggregated_candidates.sort_values(
    by=['combined_score', 'candidate_priority'], ascending=[False, False]
).reset_index(drop=True).index + 1

# Select top 50 candidates globally
top_50_candidates = aggregated_candidates[aggregated_candidates['global_rank'] <= 50]

# Display the final top 50 candidates
print(top_50_candidates[['Git_Contributor_ID', 'Git_UserName', 'combined_score', 'candidate_priority', 'global_rank', 'target']])

# Save the final results to a CSV file
top_50_candidates.to_csv('top_50_candidates.csv', index=False)

# Save the engineered features to a new CSV file
engineered_features.to_csv('contributor_evaluation_metrics.csv', index=False)
print("Engineered features saved to 'contributor_evaluation_metrics.csv'.")