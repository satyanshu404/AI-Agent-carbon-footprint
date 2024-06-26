import streamlit as st
import os
import logging
import json
from dotenv import load_dotenv
import constants
from langchain_openai import ChatOpenAI
from tools import tools, utils
from tools.create_corpus import create_json_summary
from tools.get_all_files_of_directory import files_in_directory
from prompts import prompts
from langchain.tools.render import render_text_description
from langchain.prompts import ChatPromptTemplate
from langchain_core.utils.function_calling import convert_to_openai_function
from langchain.prompts import MessagesPlaceholder
from langchain.agents import AgentExecutor
from langchain.schema.agent import AgentFinish
from langchain.schema.runnable import RunnablePassthrough
from langchain.memory import ConversationBufferMemory
from langchain.agents.format_scratchpad import format_to_openai_functions
from langchain.agents.output_parsers import OpenAIFunctionsAgentOutputParser
from langchain_community.callbacks.streamlit import StreamlitCallbackHandler

# load environment variables
load_dotenv()
# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# '''
# 1. take the files as input, store and read it.
# 2. search for the products for which data model can be created.
# 3. create the data model for each product.
# '''

class DataModelGenerator:
    def __init__(self):
        self.tools = [files_in_directory, tools.read_files, tools.get_product_names, tools.ai_assistant, tools.reterive_data]
        self.data_model_list = constants.DataModelGeneratorConstants().DATA_MODEL_LIST 
        
        self.repo_path = constants.DataModelGeneratorConstants.REPO_PATH

        # temporary file for downloading the data 
        if not os.path.exists(self.repo_path):
            os.makedirs(self.repo_path)
            logging.log(logging.INFO, f"Created repository path: {self.repo_path}")
    
    def get_prompt(self, tools_list: str, tool_names: str):
        prompt = ChatPromptTemplate.from_messages([
            ("system", prompts.get_react_prompt().format(tools_list, tool_names)),
            ("user", prompts.get_data_model_generator_prompt().format(self.data_model_output_schema)),
            MessagesPlaceholder(variable_name="chat_history"),
            ("user", "File paths: {input}"),
            ("user", f"data_model_type: {self.data_model_type}"),
            MessagesPlaceholder(variable_name="agent_scratchpad")
        ])
        return prompt
    
    def get_tool_description(self, tools: list):
        tools_list=render_text_description(list(tools))
        tool_names=", ".join([t.name for t in tools])
        return tools_list, tool_names
    
    def get_functions(self, tools: list):
        return [convert_to_openai_function(f) for f in tools]
    
    def search_engine_agent(self):
        tools_list, tool_names = self.get_tool_description(self.tools)
        functions = self.get_functions(self.tools)
        prompt = self.get_prompt(tools_list, tool_names)
        
        llm = ChatOpenAI(model=constants.Constants.MODEL_NAME).bind(functions=functions)
        output_parser = OpenAIFunctionsAgentOutputParser()
        chain = prompt | llm | output_parser
        agent_chain = RunnablePassthrough.assign(agent_scratchpad= lambda x: format_to_openai_functions(x["intermediate_steps"])) | chain
        memory = ConversationBufferMemory(return_messages=True,memory_key="chat_history")

        agent_executor = AgentExecutor(agent=agent_chain, tools=self.tools, verbose=True, memory=memory, return_intermediate_steps=True)
        
        return agent_executor
    
    def save_file(self, file_path: str, content: str):
        with open(file_path, "wb") as f:
            f.write(content)
        
    
    def invoke_agent(self):
        try:
            logging.log(logging.INFO, "Running the data model generator agent...")

            st.title("Data Model Generator Agent")

            # upload files
            uploaded_files = st.file_uploader("Choose files", accept_multiple_files=True)

            file_paths = []
            # save the files
            if uploaded_files:
                for file in uploaded_files:
                    file_path = os.path.join(self.repo_path, file.name)
                    self.save_file(file_path, file.getbuffer())
                    file_paths.append(file_path)
                    
                st.success(f"{len(uploaded_files)} files uploaded successfully!")
            
            self.data_model_type = st.selectbox(
                'Choose data model:',
                self.data_model_list
            ).lower()

            st.write(f"Selected data model: {self.data_model_type}")

            self.data_model_output_schema = utils.ReadFiles().read_txt(constants.DataModelGeneratorConstants().DATA_MODEL_PATH[self.data_model_type])

            agent_executor = self.search_engine_agent()
            st_callback = StreamlitCallbackHandler(st.container())
            

            if st.button("Run Agent"):
                with st.spinner("Processing..."):
                    response = agent_executor.invoke(
                        {"input": file_paths}, 
                        callback_handler=st_callback)
                    if response['output']:
                        st.write(response['output'])
        except Exception as e:
            logging.log(logging.ERROR, f"An error occurred: {str(e)}")
            st.write(f"An error occurred: {str(e)}")
        
if __name__ == "__main__":
    data_model_generator = DataModelGenerator()
    data_model_generator.invoke_agent()