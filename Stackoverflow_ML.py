import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import SVC
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report
from sklearn.feature_selection import SelectKBest, f_classif
from sklearn.preprocessing import LabelEncoder
import sqlite3
# Step 0: Load your dataset (replace this with your actual dataset)
conn = sqlite3.connect('Stackoverflow.db')

df  = pd.read_sql('SELECT * FROM merged_table', conn)

# Close the connection after fetching data
conn.close()



# Step 1: Split the dataset into unseen_data (70%) and working_data (30%)
unseen_data, working_data = train_test_split(df, test_size=0.3, random_state=42)

# Step 2: Assign weights to features
weights = {
    'total_badges': 0.10,
    'badge_score': 0.15,
    'reputation': 0.15,
    'total_questions': 0.10,
    'total_answered_questions': 0.10,
    'total_accepted_answers': 0.10,
    'acceptance_rate': 0.10,
    'avg_score': 0.10,
    'quality_score': 0.10
}

# Step 3: Calculate the weighted score on working_data
working_data['weighted_score'] = (
    working_data['total_badges'] * weights['total_badges'] +
    working_data['badge_score'] * weights['badge_score'] +
    working_data['reputation'] * weights['reputation'] +
    working_data['total_questions'] * weights['total_questions'] +
    working_data['total_answered_questions'] * weights['total_answered_questions'] +
    working_data['total_accepted_answers'] * weights['total_accepted_answers'] +
    working_data['acceptance_rate'] * weights['acceptance_rate'] +
    working_data['avg_score'] * weights['avg_score'] +
    working_data['quality_score'] * weights['quality_score']
)

# Step 4: Classify candidates based on the weighted score
threshold = working_data['weighted_score'].quantile(0.75)
working_data['is_good_candidate'] = np.where(working_data['weighted_score'] > threshold, '1', '0')
print("Class Distribution in Working Data:\n", working_data['is_good_candidate'].value_counts())

# Step 5: Encode the target variable into numeric values
label_encoder = LabelEncoder()
working_data['is_good_candidate_encoded'] = label_encoder.fit_transform(working_data['is_good_candidate'])

# Step 6: Feature Selection on working_data
X = working_data.drop(columns=['user_id', 'is_good_candidate', 'is_good_candidate_encoded', 'weighted_score'])
y = working_data['is_good_candidate_encoded']

# Perform feature selection using SelectKBest
selector = SelectKBest(f_classif, k=20)  # Select top 20 features
X_new = selector.fit_transform(X, y)

# Get the selected features
selected_features = X.columns[selector.get_support()]
print("\nSelected Features:\n", selected_features)

# Step 7: Further split the working_data into validation_data (40%) and train_test_data (60%)
validation_data, train_test_data = train_test_split(working_data, test_size=0.6, random_state=42)

# Prepare the data for training
X_train = train_test_data[selected_features]
y_train = train_test_data['is_good_candidate_encoded']

X_val = validation_data[selected_features]
y_val = validation_data['is_good_candidate_encoded']

# Step 8: Define Hyperparameter Grids
rf_params = {
    'n_estimators': [100, 200, 300],
    'max_depth': [None, 10, 20, 30],
    'min_samples_split': [2, 5, 10]
}

svm_params = {
    'C': [0.1, 1, 10],
    'kernel': ['linear', 'rbf'],
    'gamma': ['scale', 'auto']
}

lr_params = {
    'C': [0.1, 1, 10],
    'penalty': ['l2'],
    'solver': ['lbfgs', 'liblinear'],
    'max_iter': [1000]
}

# Step 9: Perform Hyperparameter Tuning
def tune_model(model, params, X_train, y_train, X_val, y_val, model_name):
    print(f"\nTuning {model_name}...")
    grid_search = GridSearchCV(model, params, cv=5, scoring='accuracy')
    grid_search.fit(X_train, y_train)
    best_model = grid_search.best_estimator_
    y_pred = best_model.predict(X_val)
    accuracy = accuracy_score(y_val, y_pred)
    print(f"Best Parameters: {grid_search.best_params_}")
    print(f"Validation Accuracy: {accuracy}")
    return best_model, accuracy

# Tune RandomForest
rf_best_model, rf_accuracy = tune_model(
    RandomForestClassifier(random_state=42), rf_params, X_train, y_train, X_val, y_val, "RandomForest"
)

# Tune SVM
svm_best_model, svm_accuracy = tune_model(
    SVC(random_state=42), svm_params, X_train, y_train, X_val, y_val, "SVM"
)

# Tune LogisticRegression
lr_best_model, lr_accuracy = tune_model(
    LogisticRegression(random_state=42), lr_params, X_train, y_train, X_val, y_val, "LogisticRegression"
)

# Step 10: Compare the Best Models
best_models = {
    'RandomForest': (rf_best_model, rf_accuracy),
    'SVM': (svm_best_model, svm_accuracy),
    'LogisticRegression': (lr_best_model, lr_accuracy)
}

# Select the overall best model
overall_best_model_name = max(best_models, key=lambda k: best_models[k][1])
overall_best_model, overall_best_accuracy = best_models[overall_best_model_name]
print(f"\nOverall Best Model: {overall_best_model_name} with Accuracy: {overall_best_accuracy}")

# Step 11: Train the Overall Best Model on Full Working Data
working_data = pd.concat([train_test_data, validation_data])
X_working = working_data[selected_features]
y_working = working_data['is_good_candidate_encoded']
overall_best_model.fit(X_working, y_working)

# Step 12: Evaluate on Unseen Data
# Calculate the weighted score for unseen_data
unseen_data['weighted_score'] = (
    unseen_data['total_badges'] * weights['total_badges'] +
    unseen_data['badge_score'] * weights['badge_score'] +
    unseen_data['reputation'] * weights['reputation'] +
    unseen_data['total_questions'] * weights['total_questions'] +
    unseen_data['total_answered_questions'] * weights['total_answered_questions'] +
    unseen_data['total_accepted_answers'] * weights['total_accepted_answers'] +
    unseen_data['acceptance_rate'] * weights['acceptance_rate'] +
    unseen_data['avg_score'] * weights['avg_score'] +
    unseen_data['quality_score'] * weights['quality_score']
)

# Predict on unseen data
unseen_X = unseen_data[selected_features]
unseen_y_pred = overall_best_model.predict(unseen_X)
unseen_data['predicted_is_good_candidate'] = unseen_y_pred

# Step 13: Get the good candidates list
good_candidates = unseen_data[unseen_data['predicted_is_good_candidate'] == 1]

good_candidates.to_sql('good_candidates_table', conn, if_exists='replace', index=False)

conn.commit()
conn.close()