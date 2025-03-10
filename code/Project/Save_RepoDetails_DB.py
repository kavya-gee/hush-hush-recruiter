import pandas as pd
from DB_Opr import create_table,insert_data, select_data
import configparser


config = configparser.ConfigParser()
config.read('config.ini')  # Path to your config file

# Extract database connection details
db_config = config['database']
dbname = db_config['dbname']
user = db_config['user']
password = db_config['password']
host = db_config['host']
port = db_config['port']

df = pd.read_csv('top_50_repos.csv')

Repo_columns = {
    "Repo_Name": "TEXT",
    "Repo_Owner": "TEXT",
    "Repo_URL": "TEXT",
    "Stars": "INT",
    "Forks": "INT",
    "Number_of_Contributors": "INT",
    "Pull_Requests_Open":"INT",
    "Pull_Requests_Closed":"TEXT",
    "Open_Issues":"INT",
    "Language": "TEXT"
}


create_table(
    dbname=dbname,
    user=user,
    password=password,
    host=host,
    port=port,
    table_name="Repos_Details",
    columns=Repo_columns
)

insert_data(
    dbname=dbname,
    user=user,
    password=password,
    host=host,
    port=port,
    table_name="Repos_Details",
    df=df,
    columns=list(Repo_columns.keys())
)

select_query = """
SELECT * FROM Repos_Details
"""

# Fetch data using the custom SELECT query
df_selected = select_data(
    dbname=dbname,
    user=user,
    password=password,
    host=host,
    port=port,
    query=select_query
)

# Display the fetched data
print("Fetched Data:")
print(df_selected)