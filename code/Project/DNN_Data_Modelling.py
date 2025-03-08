import pandas as pd
import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, Dropout
from tensorflow.keras.layers import Input
import pickle

# Step 1: Read the CSV file into a DataFrame
df = pd.read_csv('Contributors_Details_Final.csv')

# Step 2: Replace blank values with 0 in the specified columns
columns_to_fill = ['PRs_Created', 'PRs_Merged', 'PRs_Closed']
df[columns_to_fill] = df[columns_to_fill].fillna(0)

# Step 3: Select features for clustering
features_for_clustering = [
    'Number_of_Commits', 'Followers', 'number_of_additions', 'number_of_deletions',
    'PRs_Created', 'PRs_Merged', 'PRs_Closed', 'PRs_reviewed', 'Issues_created', 'Issues_closed'
]

# Extract the relevant features
X_clustering = df[features_for_clustering]

# Normalize the features for clustering
scaler_clustering = StandardScaler()
X_clustering_scaled = scaler_clustering.fit_transform(X_clustering)

# Step 4: Apply KMeans clustering
kmeans = KMeans(n_clusters=2, random_state=42)  # Two clusters: 0 and 1
df['target'] = kmeans.fit_predict(X_clustering_scaled)

# Step 5: Create a new DataFrame for engineered features
engineered_features = pd.DataFrame()

# Feature Engineering
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

# Efficiency Features
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

# Add identifier columns
engineered_features['Git_Contributor_ID'] = df['Git_Contributor_ID']
engineered_features['Git_UserName'] = df['Git_UserName']
engineered_features['Repo_Name'] = df['Repo_Name']
engineered_features['Repo_Owner'] = df['Repo_Name']
engineered_features['Type_of_User'] = df['Type_of_User']
engineered_features['target'] = df['target']

# Step 6: Train the DNN
# Filter rows where Type_of_User == "User"
engineered_features = engineered_features[engineered_features['Type_of_User'] == 'User']

# Prioritize repeated candidates
candidate_counts = engineered_features['Git_Contributor_ID'].value_counts()
engineered_features['candidate_priority'] = engineered_features['Git_Contributor_ID'].map(candidate_counts)

# Separate features and target
X = engineered_features.drop(columns=['target', 'Git_Contributor_ID', 'Git_UserName', 'Repo_Name', 'Repo_Owner', 'Type_of_User'])  # Drop identifiers and categorical features
y = engineered_features['target']

# Split the data into training and testing sets
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=32)

# Normalize numerical features
scaler = StandardScaler()
X_train = scaler.fit_transform(X_train)
X_test = scaler.transform(X_test)

# Define the DNN model
model = Sequential([
    Input(shape=(X_train.shape[1],)),  # Explicit Input layer
    Dense(64, activation='relu'),
    Dropout(0.2),
    Dense(32, activation='relu'),
    Dropout(0.2),
    Dense(1, activation='sigmoid')
])

# Compile the model
model.compile(optimizer='adam', loss='binary_crossentropy', metrics=['accuracy'])

# Train the model
history = model.fit(X_train, y_train, epochs=90, batch_size=32, validation_split=0.2)

# Evaluate the model
loss, accuracy = model.evaluate(X_test, y_test)
print(f"Test Accuracy: {accuracy:.4f}")

# Save the model and scaler
with open('trained_model.pkl', 'wb') as f:
    pickle.dump(model, f)

with open('scaler.pkl', 'wb') as f:
    pickle.dump(scaler, f)

# Step 7: Apply Ranking Logic
# Predict probabilities for all candidates
engineered_features['predicted_probability'] = model.predict(scaler.transform(
    engineered_features.drop(columns=['target', 'Git_Contributor_ID', 'Git_UserName', 'Repo_Name', 'Repo_Owner', 'Type_of_User'])
))

# Define weights for each factor
weight_predicted_probability = 0.6
weight_candidate_priority = 0.4

# Calculate combined score
engineered_features['combined_score'] = (
    (weight_predicted_probability * engineered_features['predicted_probability']) +
    (weight_candidate_priority * engineered_features['candidate_priority'])
)

# Rank candidates within each repository based on the combined score
engineered_features['rank_in_repo'] = engineered_features.groupby('Repo_Name')['combined_score'].rank(ascending=True)

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