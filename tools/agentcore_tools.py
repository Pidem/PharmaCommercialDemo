import json
from langchain_core.tools import tool
from bedrock_agentcore.tools.code_interpreter_client import CodeInterpreter


def call_tool(client, tool_name: str, arguments):
    """Helper function to invoke sandbox tools"""
    response = client.invoke(tool_name, arguments)
    for event in response["stream"]:
        return json.dumps(event["result"])


def extract_png_from_aws_response(response):
    """Extract PNG from the specific AWS response structure."""
    stream = response['stream']
    
    try:
        for event in stream:
            if 'result' in event:
                result = event['result']
                
                if 'content' in result and isinstance(result['content'], list):
                    for content_item in result['content']:
                        if (content_item.get('type') == 'resource' and 
                            'resource' in content_item):
                            
                            resource = content_item['resource']
                            
                            if (resource.get('mimeType') == 'image/png' and 
                                'blob' in resource):
                                
                                png_data = resource['blob']
                                print(f"Found PNG data: {len(png_data)} bytes")
                                
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
    """Complete function to extract and save PNG from AWS response."""
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
    print(f"📄 Code to execute:\n{code[:200]}{'...' if len(code) > 200 else ''}")
    
    code_client = CodeInterpreter('us-west-2')
    code_client.start()
    code_session_id = code_client.start()

    data_file = "temp_data.csv"

    try:
        with open(data_file, 'r', encoding='utf-8') as data_file_content:
            data_file_content = data_file_content.read()
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

    execute_response = code_client.invoke("executeCode", {
        "code": code,
        "language": "python",
        "clearContext": False
    })
    
    listing_files = call_tool(code_client, "listFiles", {"path": ""})
    print("\nFiles in sandbox after:")
    print(listing_files)

    read_response = code_client.invoke("readFiles", {"paths": ["chart.png"]})
    print("downloading response")
    save_png_from_aws_response(read_response, 'chart.png')

    code_client.stop()
    print("✅ Session stopped")
    for event in execute_response["stream"]:
        return f"Execution results: {json.dumps(event['result'])}"


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
