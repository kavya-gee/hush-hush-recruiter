import psycopg2
import pandas as pd

def create_table(dbname, user, password, host, port, table_name, columns):
    """
    Creates a table in PostgreSQL with the specified columns.

    Args:
        dbname (str): Name of the PostgreSQL database.
        user (str): PostgreSQL username.
        password (str): PostgreSQL password.
        host (str): PostgreSQL host (e.g., 'localhost').
        port (str): PostgreSQL port (e.g., '5432').
        table_name (str): Name of the table to create.
        columns (dict): Dictionary of column names and their data types.
    """
    # Connect to PostgreSQL
    conn = psycopg2.connect(
        dbname=dbname,
        user=user,
        password=password,
        host=host,
        port=port
    )
    cursor = conn.cursor()
    
    # Generate the CREATE TABLE query dynamically
    columns_with_types = [f"{col} {dtype}" for col, dtype in columns.items()]
    create_table_query = f"""
    CREATE TABLE IF NOT EXISTS {table_name} (
        {', '.join(columns_with_types)}
    );
    """
    
    # Execute the query
    cursor.execute(create_table_query)
    conn.commit()
    cursor.close()
    conn.close()
    print(f"Table '{table_name}' created successfully.")


def insert_data(dbname, user, password, host, port, table_name, df, columns):
    """
    Inserts data into a PostgreSQL table.

    Args:
        dbname (str): Name of the PostgreSQL database.
        user (str): PostgreSQL username.
        password (str): PostgreSQL password.
        host (str): PostgreSQL host (e.g., 'localhost').
        port (str): PostgreSQL port (e.g., '5432').
        table_name (str): Name of the table to insert data into.
        df (pd.DataFrame): DataFrame containing the data to insert.
        columns (list): List of column names to insert.
    """
    # Connect to PostgreSQL
    conn = psycopg2.connect(
        dbname=dbname,
        user=user,
        password=password,
        host=host,
        port=port
    )
    cursor = conn.cursor()
    
    # Generate the INSERT query dynamically
    insert_query = f"""
    INSERT INTO {table_name} ({', '.join(columns)}) 
    VALUES ({', '.join(['%s'] * len(columns))});
    """
    
    # Insert data row by row
    for _, row in df.iterrows():
        cursor.execute(insert_query, tuple(row[col] for col in columns))
    
    conn.commit()
    cursor.close()
    conn.close()
    print(f"Data inserted into '{table_name}' successfully.")


def select_data(dbname, user, password, host, port, query):
    """
    Fetches data from a PostgreSQL table using a custom SELECT query.

    Args:
        dbname (str): Name of the PostgreSQL database.
        user (str): PostgreSQL username.
        password (str): PostgreSQL password.
        host (str): PostgreSQL host (e.g., 'localhost').
        port (str): PostgreSQL port (e.g., '5432').
        query (str): The SELECT query to execute.

    Returns:
        pd.DataFrame: A DataFrame containing the selected data.
    """
    # Connect to PostgreSQL
    conn = psycopg2.connect(
        dbname=dbname,
        user=user,
        password=password,
        host=host,
        port=port
    )
    
    # Fetch data into a DataFrame
    df = pd.read_sql_query(query, conn)
    
    conn.close()
    print(f"Data fetched using the query: '{query}'")
    return df