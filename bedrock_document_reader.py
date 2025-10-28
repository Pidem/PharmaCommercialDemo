import boto3

def analyze_document_with_bedrock(file_path, question="Please analyze this document and provide a summary."):
    """Use Bedrock converse API with vision capabilities to analyze document."""
    bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')
    
    with open(file_path, "rb") as doc_file:
        doc_bytes = doc_file.read()
    
    doc_message = {
        "role": "user",
        "content": [
            {
                "document": {
                    "name": "Document 1",
                    "format": "pdf",
                    "source": {
                        "bytes": doc_bytes
                    }
                }
            },
            {"text": question}
        ]
    }
    
    response = bedrock.converse(
        modelId="us.anthropic.claude-sonnet-4-5-20250929-v1:0",
        messages=[doc_message],
        inferenceConfig={
            "maxTokens": 1000,
            "temperature": 0.1
        }
    )
    
    return response['output']['message']['content'][0]['text']

def main():
    document_path = "data/cosentyx.pdf"
    
    try:
        analysis = analyze_document_with_bedrock(document_path)
        print("Document Analysis:")
        print("=" * 50)
        print(analysis)
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()