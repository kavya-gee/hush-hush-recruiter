import asyncio
import aiohttp
import pandas as pd
import time
import sqlite3
import ast

## import all the data frames

conn = sqlite3.connect('Stackoverflow.db')


df_user_profile = pd.read_sql('SELECT * FROM user_profile', conn)

df_questions_asked = pd.read_sql('SELECT * FROM questions_asked', conn)

df_answers_provided =  pd.read_sql('SELECT * FROM answers_provided', conn)

df_comments = pd.read_sql('SELECT * FROM comments', conn)

conn.close()

#feature enginering and cleaning of the data





df_user_profile = df_user_profile.drop_duplicates(subset=["user_id"], keep="first")
columns_to_drop = [
    "is_employee",
    "user_type",
    "location",
    "website_url",
    "link",
    "display_name",
    "creation_date","profile_image","collectives"
]


df_user_profile_cleaned = df_user_profile.drop(columns=columns_to_drop)


df_user_profile_cleaned['accept_rate'].fillna(0, inplace=True)



df_user_profile_cleaned['badge_counts'] = df_user_profile_cleaned['badge_counts'].apply(ast.literal_eval)  # Convert string to dictionary

df_user_profile_cleaned['bronze_badges'] = df_user_profile_cleaned['badge_counts'].apply(lambda x: x.get('bronze', 0))
df_user_profile_cleaned['silver_badges'] = df_user_profile_cleaned['badge_counts'].apply(lambda x: x.get('silver', 0))
df_user_profile_cleaned['gold_badges'] = df_user_profile_cleaned['badge_counts'].apply(lambda x: x.get('gold', 0))

df_user_profile_cleaned['total_badges'] = df_user_profile_cleaned['bronze_badges'] + df_user_profile_cleaned['silver_badges'] + df_user_profile_cleaned['gold_badges']
df_user_profile_cleaned['badge_score'] = (df_user_profile_cleaned['bronze_badges'] * 1) + (df_user_profile_cleaned['silver_badges'] * 3) + (df_user_profile_cleaned['gold_badges'] * 10)


df_user_profile_cleaned['reputation_variability'] = df_user_profile_cleaned[['reputation_change_year', 'reputation_change_quarter', 'reputation_change_month', 'reputation_change_week']].std(axis=1)





# feature enginering for answer_provided
df_answers_provided = df_answers_provided.drop_duplicates()
user_stats = df_answers_provided.groupby("user_id").agg(
    total_answers=('answer_id', 'count'),  # Count of answers provided
    accepted_answers=('is_accepted', 'sum'),  # Count of accepted answers
    avg_score=('score', 'mean'),  # Average score of answers
    first_answer=('creation_date', 'min'),  # First answer date
    last_answer=('creation_date', 'max')  # Last answer date
).reset_index()  # Reset index to make user_id a column


user_stats['acceptance_rate'] = (user_stats['accepted_answers'] / user_stats['total_answers']) * 100

user_stats['first_answer'] = pd.to_datetime(user_stats['first_answer'], unit='s')
user_stats['last_answer'] = pd.to_datetime(user_stats['last_answer'], unit='s')

user_stats['activity_duration'] = (user_stats['last_answer'] - user_stats['first_answer']).dt.days
user_stats['answers_per_day'] = user_stats['total_answers'] / user_stats['activity_duration']
user_stats['quality_score'] = (user_stats['avg_score'] * user_stats['acceptance_rate']) / 100
user_stats['engagement_level'] = pd.cut(
    user_stats['total_answers'],
    bins=[0, 10, 50, float('inf')],
    labels=[0, 1, 2]
)

df_answers_provided = user_stats




#cleaning and the feature enginering for comments

df_comments = df_comments.drop_duplicates()
df_comments['creation_date'] = pd.to_datetime(df_comments['creation_date'], unit='s')
df_comments['comment_year'] = df_comments['creation_date'].dt.year
df_comments['comment_month'] = df_comments['creation_date'].dt.month
df_comments['comment_day'] = df_comments['creation_date'].dt.day
df_comments['comment_hour'] = df_comments['creation_date'].dt.hour
df_comments['comment_day_of_week'] = df_comments['creation_date'].dt.dayofweek

user_stats = df_comments.groupby('user_id').agg(
    total_comments=('comment_id', 'count'),
    avg_comment_score=('score', 'mean'),
    total_replies=('reply_to_user', 'count')
).reset_index()

df_comments = df_comments.merge(user_stats, on='user_id', how='left')
df_comments['is_reply'] = df_comments['reply_to_user'].notna().astype(int)
df_comments['is_high_score'] = (df_comments['score'] > df_comments['score'].quantile(0.75)).astype(int)

df_comments = df_comments.drop(columns=['owner', 'content_license',"reply_to_user"])

user_aggregated_stats = df_comments.groupby('user_id').agg(
    total_comments=('comment_id', 'count'),
    avg_comment_score=('score', 'mean'),
    total_replies=('is_reply', 'sum'),
    total_high_score_comments=('is_high_score', 'sum')  ).reset_index()

df_comments=user_aggregated_stats



# feature enginering and cleaning

df_questions_asked = df_questions_asked.drop_duplicates()
df_questions_asked['creation_date'] = pd.to_datetime(df_questions_asked['creation_date'], unit='s')
df_questions_asked['last_activity_date'] = pd.to_datetime(df_questions_asked['last_activity_date'], unit='s')
df_questions_asked['last_edit_date'] = pd.to_datetime(df_questions_asked['last_edit_date'], unit='s')

df_questions_asked['creation_year'] = df_questions_asked['creation_date'].dt.year
df_questions_asked['creation_month'] = df_questions_asked['creation_date'].dt.month
df_questions_asked['creation_day'] = df_questions_asked['creation_date'].dt.day
df_questions_asked['creation_hour'] = df_questions_asked['creation_date'].dt.hour
df_questions_asked['creation_day_of_week'] = df_questions_asked['creation_date'].dt.dayofweek


user_stats = df_questions_asked.groupby('user_id').agg(
    total_questions=('question_id', 'count'),
    avg_question_score=('score', 'mean'),
    total_answered_questions=('is_answered', 'sum')
).reset_index()
df_questions_asked = df_questions_asked.merge(user_stats, on='user_id', how='left')


df_questions_asked['is_answered'] = df_questions_asked['is_answered'].astype(int)
df_questions_asked['has_accepted_answer'] = df_questions_asked['accepted_answer_id'].notna().astype(int)

df_questions_asked['num_tags'] = df_questions_asked['tags'].apply(lambda x: len(x.split(',')))
popular_tags = ['python', 'javascript', 'java', 'c#', 'php']
for tag in popular_tags:
    df_questions_asked[f'tag_{tag}'] = df_questions_asked['tags'].apply(lambda x: 1 if tag in x else 0)

df_questions_asked['is_popular'] = (df_questions_asked['view_count'] > df_questions_asked['view_count'].quantile(0.75)).astype(int)


df_questions_asked['has_accepted_answer'] = df_questions_asked['accepted_answer_id'].notna().astype(int)
user_stats = df_questions_asked.groupby('user_id').agg(
    total_questions=('question_id', 'count'),
    total_accepted_answers=('has_accepted_answer', 'sum')
).reset_index()

# Calculate acceptance rate
user_stats['acceptance_rate'] = (user_stats['total_accepted_answers'] / user_stats['total_questions']) * 100

# Merge back with df_questions_asked
df_questions_asked = df_questions_asked.merge(user_stats, on='user_id', how='left')
df_questions_asked['has_accepted_answer_vs_answer_count'] = df_questions_asked['has_accepted_answer'] / df_questions_asked['answer_count']

user_summary = df_questions_asked.groupby('user_id').agg(
    total_questions=('question_id', 'count'),  # Total questions asked
    avg_question_score=('score', 'mean'),      # Average score of questions
    avg_view_count=('view_count', 'mean'),     # Average view count
    avg_answer_count=('answer_count', 'mean'), # Average number of answers per question
    total_answered_questions=('is_answered', 'sum'),  # Total answered questions
    total_accepted_answers=('has_accepted_answer', 'sum'),  # Total accepted answers
    acceptance_rate=('acceptance_rate', 'mean'),  # Average acceptance rate
    avg_num_tags=('num_tags', 'mean'),           # Average number of tags per question
    total_popular_questions=('is_popular', 'sum'),  # Total popular questions
    total_python_tags=('tag_python', 'sum'),    # Total questions with Python tag
    total_javascript_tags=('tag_javascript', 'sum'),  # Total questions with JavaScript tag
    total_java_tags=('tag_java', 'sum'),        # Total questions with Java tag
    total_csharp_tags=('tag_c#', 'sum'),        # Total questions with C# tag
    total_php_tags=('tag_php', 'sum'),          # Total questions with PHP tag
    first_question_date=('creation_date', 'min'),  # Date of first question
    last_question_date=('creation_date', 'max'),   # Date of last question
    active_days=('creation_date', lambda x: (x.max() - x.min()).days)  # Active days
).reset_index()

user_summary['avg_time_between_questions'] = user_summary['active_days'] / user_summary['total_questions']
user_summary['is_active'] = (user_summary['last_question_date'] > pd.Timestamp.now() - pd.Timedelta(days=180)).astype(int)

user_summary['pct_popular_questions'] = (user_summary['total_popular_questions'] / user_summary['total_questions']) * 100

user_summary['avg_time_between_questions'] = user_summary['active_days'] / user_summary['total_questions']
user_summary['is_active'] = (user_summary['last_question_date'] > pd.Timestamp.now() - pd.Timedelta(days=180)).astype(int)

user_summary['pct_popular_questions'] = (user_summary['total_popular_questions'] / user_summary['total_questions']) * 100

df_questions_asked=user_summary

columns_to_drop = [
    "is_active",
    "avg_time_between_questions",
    "active_days",
    "last_question_date",
    "first_question_date"]


df_questions_asked = df_questions_asked.drop(columns=columns_to_drop)



# merge it

merged_df = pd.merge(df_questions_asked, df_comments, on='user_id', how='outer', suffixes=('_question', '_comment'))


merged_df = pd.merge(merged_df, df_user_profile, on='user_id', how='outer', suffixes=('', '_profile'))

merged_df = pd.merge(merged_df, df_answers_provided, on='user_id', how='outer', suffixes=('', '_answer'))




merged_df = merged_df.drop(columns=['badge_counts',"first_answer","last_answer"])
merged_df = merged_df.drop_duplicates()
numeric_columns = merged_df.select_dtypes(include=['float64', 'int64']).columns
merged_df[numeric_columns] = merged_df[numeric_columns].fillna(0)

conn = sqlite3.connect('Stackoverflow.db')
merged_df.to_sql('merged_table', conn, if_exists='replace', index=False)

conn.commit()
conn.close()