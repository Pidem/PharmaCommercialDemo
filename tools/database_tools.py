import sqlite3
import pandas as pd
import boto3
import re
from langchain_core.tools import tool

BEDROCK_MODEL = 'amazon.nova-premier-v1:0'

def _get_schema():
    """Helper function to get database schema."""
    conn = sqlite3.connect('data/pharma_sales.db')
    cursor = conn.cursor()

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()

    schema = {}
    for table in tables:
        table_name = table[0]
        cursor.execute(f"PRAGMA table_info({table_name});")
        columns = cursor.fetchall()
        schema[table_name] = [col[1] for col in columns]

    conn.close()
    return "\n".join([f"- {table}: {', '.join(columns)}" for table, columns in schema.items()])


@tool
def get_database_schema() -> str:
    """Retrieve database schema dynamically."""
    print("🔧 Tool Called: get_database_schema")
    result = _get_schema()
    table_count = len(result.split('\n'))
    print(f"✅ Schema retrieved: {table_count} tables found")
    return result


@tool
def generate_and_execute_sql(question: str) -> str:
    """Generate SQL query and execute it based on user question."""
    print(f"🔧 Tool Called: generate_and_execute_sql with question: '{question}'")

    bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')
    schema = _get_schema()

    prompt = f"""Database schema:
                {schema}

                User question: {question}

                Generate a SQL query to answer this question. Return only the SQL query, no explanations."""

    print("🤖 Generating SQL query with Bedrock...")
    response = bedrock.converse(
        modelId=f"us.{BEDROCK_MODEL}",
        messages=[{"role": "user", "content": [{"text": prompt}]}],
        inferenceConfig={"maxTokens": 500, "temperature": 0.1}
    )

    sql_query = response['output']['message']['content'][0]['text'].strip()
    sql_query = re.sub(r'```sql\n?|```\n?', '', sql_query)
    print(f"📝 Generated SQL: {sql_query}")

    print("💾 Executing SQL query...")
    conn = sqlite3.connect('data/pharma_sales.db')
    df = pd.read_sql_query(sql_query, conn)
    conn.close()

    csv_filename = "temp_data.csv"
    df.to_csv(csv_filename, index=False)
    print(f"✅ SQL executed successfully: {len(df)} rows saved to {csv_filename}")

    return f"SQL Query: {sql_query}\nData saved to: {csv_filename}\nRows: {len(df)}. Data header: {df.head()}"
