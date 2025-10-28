import sqlite3
import pandas as pd
import boto3
import re
import json
from langchain_core.tools import tool
from langchain.agents import create_agent

from bedrock_agentcore.tools.code_interpreter_client import CodeInterpreter

import json
import base64
from botocore.eventstream import EventStream


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
    print(
        f"🔧 Tool Called: generate_and_execute_sql with question: '{question}'")

    bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')
    schema = _get_schema()

    prompt = f"""Database schema:
                {schema}

                User question: {question}

                Generate a SQL query to answer this question. Return only the SQL query, no explanations."""

    print("🤖 Generating SQL query with Bedrock...")
    response = bedrock.converse(
        modelId="us.anthropic.claude-sonnet-4-5-20250929-v1:0",
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
    print(
        f"✅ SQL executed successfully: {len(df)} rows saved to {csv_filename}")

    return f"SQL Query: {sql_query}\nData saved to: {csv_filename}\nRows: {len(df)}"


def call_tool(client, tool_name: str, arguments):
    """Helper function to invoke sandbox tools
    
    Args:
        tool_name (str): Name of the tool to invoke
        arguments (Dict[str, Any]): Arguments to pass to the tool
        
    Returns:
        Dict[str, Any]: JSON formatted result
    """
    response = client.invoke(tool_name, arguments)
    for event in response["stream"]:
        return json.dumps(event["result"])

def extract_png_from_aws_response(response):
    """
    Extract PNG from the specific AWS response structure:
    response['stream'] -> event['result']['content'][0]['resource']['blob']
    """
    
    stream = response['stream']
    
    try:
        # Get the first (and likely only) event
        for event in stream:
            if 'result' in event:
                result = event['result']
                
                if 'content' in result and isinstance(result['content'], list):
                    for content_item in result['content']:
                        if (content_item.get('type') == 'resource' and 
                            'resource' in content_item):
                            
                            resource = content_item['resource']
                            
                            # Verify it's a PNG resource
                            if (resource.get('mimeType') == 'image/png' and 
                                'blob' in resource):
                                
                                png_data = resource['blob']
                                print(f"Found PNG data: {len(png_data)} bytes")
                                
                                # Verify PNG signature
                                if png_data.startswith(b'\x89PNG\r\n\x1a\n'):
                                    print("✅ Valid PNG signature confirmed")
                                    return png_data
                                else:
                                    print("⚠️ Data doesn't have PNG signature")
                                    return png_data
        
        print("❌ No PNG data found in expected structure")
        return None
        
    except Exception as e:
        print(f"Error extracting PNG: {e}")
        return None

def save_png_from_aws_response(response, filename='extracted_chart.png'):
    """
    Complete function to extract and save PNG from your AWS response
    """
    print(f"Extracting PNG from AWS response...")
    
    png_data = extract_png_from_aws_response(response)
    
    if png_data:
        try:
            with open(filename, 'wb') as f:
                f.write(png_data)
            print(f"✅ Successfully saved PNG as {filename}")
            print(f"File size: {len(png_data)} bytes")
            return True
        except Exception as e:
            print(f"❌ Error saving file: {e}")
            return False
    else:
        print("❌ No PNG data to save")
        return False


@tool
def execute_code_with_agentcore(csv_filename: str, code: str) -> str:
    """Execute Python code using AgentCore CodeInterpreter with uploaded CSV data."""
    print("🔧 Tool Called: execute_code_with_agentcore")
    print(
        f"📄 Code to execute:\n{code[:200]}{'...' if len(code) > 200 else ''}")
    
    code_client = CodeInterpreter('us-west-2')
    code_client.start()
    code_session_id = code_client.start()

    #read the content of the sample data file
    data_file = "temp_data.csv"

    try:
        with open(data_file, 'r', encoding='utf-8') as data_file_content:
            data_file_content = data_file_content.read()
        #print(data_file_content)
    except FileNotFoundError:
        print(f"Error: The file '{data_file}' was not found.")
    except Exception as e:
        print(f"An error occurred: {e}")


    files_to_create = [{"path": "temp_data.csv", "text": data_file_content}]
    writing_files = call_tool(code_client, "writeFiles", {"content": files_to_create})
    listing_files = call_tool(code_client, "listFiles", {"path": ""})
    print("\nFiles in sandbox:")
    print(listing_files)


    print("⚡ Executing code in AgentCore...")

    
    # Execute code in the session
    execute_response = code_client.invoke("executeCode",                        {
            "code": code,
            "language": "python",
            "clearContext": False
            }
            )
    listing_files = call_tool(code_client, "listFiles", {"path": ""})
    print("\nFiles in sandbox after:")
    print(listing_files)

    read_response = code_client.invoke("readFiles", {"paths": ["chart.png"]})
    print("downloading response")
    save_png_from_aws_response(read_response, 'chart.png')

    #Clean up and stop the code interpreter session 
    code_client.stop()
    print("✅ Session stopped")
    
    return f"Execution results: {execute_response} and files after execution: {listing_files}"


@tool
def display_chart() -> str:
    """Display the chart.png file if it exists."""
    import os
    from IPython.display import Image, display
    
    chart_path = 'chart.png'
    if os.path.exists(chart_path):
        try:
            display(Image(chart_path))
            return f"✅ Chart displayed successfully from {chart_path}"
        except Exception as e:
            return f"❌ Error displaying chart: {e}"
    else:
        return f"❌ Chart file '{chart_path}' not found"


def create_agent_executor():
    tools = [get_database_schema, generate_and_execute_sql,
             execute_code_with_agentcore, display_chart]

    agent = create_agent(
        model="bedrock:us.anthropic.claude-sonnet-4-5-20250929-v1:0",
        tools=tools,
        system_prompt="You are a pharmaceutical data analyst. Use the tools to analyze data and create visualizations using AgentCore CodeInterpreter."
    )

    return agent

def main():
    print("🚀 Starting Pharmaceutical Data Analysis Agent with AgentCore")
    print("=" * 60)

    agent = create_agent_executor()
    messages = []

    while True:
        if not messages:
            question = input("What would you like to analyze? ")
            initial_prompt = f"""Analyze: {question}. 
    
    Steps:
    1. Get the database schema
    2. Generate and execute SQL to get the data (always saved as temp_data.csv)
    3. Use execute_code_with_agentcore to create a chart with matplotlib.
       - Pass "temp_data.csv" as the first parameter
       - The CSV file will be automatically uploaded to the AgentCore session
       - Create an appropriate visualization using the uploaded data
       - Always save the chart as "chart.png"
       - IMPORTANT: The code must include:
         import matplotlib
         matplotlib.use('Agg')  # Use non-interactive backend
         import matplotlib.pyplot as plt
         import pandas as pd
       - Read data from "temp_data.csv"
       - Handle data types properly (quarter column may be string like 'Q1', 'Q2')
       - Create proper time period labels for x-axis
       - Always call plt.savefig('chart.png', bbox_inches='tight') to save the chart
       - Add print statements to confirm file creation
       - Use os.path.exists('chart.png') to verify file was created"""
            messages.append({"role": "user", "content": initial_prompt})
        else:
            follow_up = input(
                "\nAny follow-up questions? (or 'quit' to exit): ")
            if follow_up.lower() in ['quit', 'exit', 'q']:
                break
            messages.append({"role": "user", "content": follow_up})

        print(f"\n🎯 Processing request...")
        print("=" * 60)

        result = agent.invoke({"messages": messages})

        # Add assistant response to conversation history
        messages.extend(result["messages"][-1:])

        print("\n" + "=" * 60)
        print("🎉 Response:")
        print(result["messages"][-1].content)

    print("\n👋 Goodbye!")


if __name__ == "__main__":
    main()
