import boto3
import os
from langchain_core.tools import tool


@tool
def ask_pdf_question(pdf_name: str, question: str) -> str:
    """Ask a question about a PDF document using Bedrock's document analysis capabilities."""
    print(f"🔧 Tool Called: ask_pdf_question with PDF: '{pdf_name}' and question: '{question}'")
    
    # Construct file path - assume PDFs are in data/ folder
    file_path = f"data/{pdf_name}"
    if not pdf_name.endswith('.pdf'):
        file_path += '.pdf'
    
    try:
        if not os.path.exists(file_path):
            return f"❌ Error: PDF file '{file_path}' not found"
        
        bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')
        
        assert os.path.exists(file_path), f"PDF file '{file_path}' not found"

        with open(file_path, "rb") as doc_file:
            doc_bytes = doc_file.read()
        
        doc_message = {
            "role": "user",
            "content": [
                {
                    "document": {
                        "name": "Document",
                        "format": "pdf",
                        "source": {
                            "bytes": doc_bytes
                        }
                    }
                },
                {"text": question}
            ]
        }
        
        print("🤖 Analyzing PDF with Bedrock...")
        response = bedrock.converse(
            modelId="us.anthropic.claude-3-sonnet-20240229-v1:0",
            messages=[doc_message],
            inferenceConfig={
                "maxTokens": 1000,
                "temperature": 0.1
            }
        )
        
        result = response['output']['message']['content'][0]['text']
        print(f"✅ PDF analysis completed for {pdf_name}")
        return result
        
    except Exception as e:
        error_msg = f"❌ Error analyzing PDF '{pdf_name}': {str(e)}"
        print(error_msg)
        return error_msg


if __name__ == "__main__":
    result = ask_pdf_question("cosentyx.pdf", "What is the dosage recommedation?")
    print(result)
