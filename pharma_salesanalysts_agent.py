from langchain.agents import create_agent
from tools import get_database_schema, generate_and_execute_sql, execute_code_with_agentcore, display_chart, web_search, ask_pdf_question

BEDROCK_MODEL = 'amazon.nova-premier-v1:0'


def create_agent_executor():
    tools = [get_database_schema, generate_and_execute_sql,
             execute_code_with_agentcore, display_chart, web_search, ask_pdf_question]

    agent = create_agent(
        model=f"bedrock:us.{BEDROCK_MODEL}",
        tools=tools,
        system_prompt="You are a pharmaceutical data analyst. Use the tools at your disposal to help the sales rep: You can query the document database cosentyx.pdf, entresto.pdf and kesimpta.pdf to answer questions on this products. You can also query the database & create data visualizations or search the internet."
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
    
    You have access to multiple tools: 
    - You can generate and execute SQL queries on the companies own products and save the output table as a csv file (the output table will always be saved as temp_data.csv)
    - You can generate python code to generate visualisations based on a csv file
       - The CSV file will be automatically uploaded to the AgentCore session
       - Create an appropriate visualization using the uploaded data
       - Always save the resulting chart as "chart.png"
       - IMPORTANT: The code must include:
         import matplotlib
         matplotlib.use('Agg')
         import matplotlib.pyplot as plt
         import pandas as pd
       - Read data from "temp_data.csv"
       - Handle data types properly (quarter column may be string like 'Q1', 'Q2')
       - Create proper time period labels for x-axis
       - Always call plt.savefig('chart.png', bbox_inches='tight') to save the chart
       - Add print statements to confirm file creation
       - Use os.path.exists('chart.png') to verify file was created
       
    Only mention sales data for brands that are in the database.   

    When you need to learn more about the competition, search the internet using the Tavily Search tool: Generate a good search query first

       """
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
