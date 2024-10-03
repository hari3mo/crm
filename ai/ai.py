import pandas as pd
import numpy as np
import openai
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
import time
import logging
import requests
import json
from datetime import datetime

load_dotenv()
MYSQL_URI = os.getenv("MYSQL_URI")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
engine = create_engine(MYSQL_URI)
client = openai.OpenAI()
model  = 'gpt-4o-mini'

class AssistantManager:
    thread_id = None
    assistant_id = None
    
    def __init__(self, model: str = model):
        self.client = client
        self.model = model
        self.assistant = (None,)
        self.thread = (None,)
        self.run = None
        self.summary = None
        
        if AssistantManager.assistant_id:
            self.assistant = self.client.beta.assistants.retrieve(
                assistant_id=AssistantManager.assistant_id
            )
        
        if AssistantManager.thread_id:
            self.thread = self.client.beta.threads.retrieve(
                thread_id=AssistantManager.thread_id
            )
        
    def create_assistant(self, name, instructions, tools):
        if not self.assistant:
            assistant = self.client.beta.assistants.create(
                name=name,
                instructions=instructions,
                tools=tools,
                model=self.model
            )
            AssistantManager.assistant_id = assistant.id
            self.assistant = assistant
            print(f'AssistantID: {self.assistant_id}')
            
    def create_thread(self):
        if not self.thread:
            thread = self.client.beta.threads.create()
            AssistantManager.thread_id = thread.id
            AssistantManager.thread = thread
            print(f'ThreadID: {self.thread_id}')
    
    def add_message(self, role, content):
        if self.thread:
            self.client.beta.threads.messages.create(
                thread_id=self.thread_id,
                role=role,
                content=content
            )
            
    def run_assistant(self, instructions):
        if self.assistant and self.thread:
            self.run = self.client.beta.threads.runs.create(
                thread_id=self.thread_id,
                assistant_id=self.assistant_id,
                instructions=instructions,
            )
            
    def process_messages(self):
        if self.thread:
            messages = self.client.beta.threads.messages.list(
                thread_id=self.thread_id
            )
            summary = []
            last_message = messages.data[0]
            role = last_message.role
            response = last_message.content[0].text.value
            
            summary.append(response)
            self.summary = '\n'.join(summary) 
            print(f'{role.capitalize()}\n {response}')
            
    def call_required_functions(self, required_actions):
        if not self.run:
            return
        
        tools_outputs = []
        for action in required_actions['tool_calls']:
            func_name = action['function']['name']
            arguments = json.loads(action['funtion']['arguments'])
            
            if func_name == None:
                output = ...
        
    def wait_for_completed(self):
        if self.thread and self.run:
            while True:
                time.sleep(5)
                run_status = self.client.threads.runs.retrieve(
                    thread_id=self.thread_id,
                    run_id=self.run.id
                )
                print(f'Status: {run_status.model_dump_json(indent=4)}')
                
                if run_status.status == 'completed':
                    self.process_messages()
                    break
                elif run_status.status == 'requires_action':
                    print('Function calling in progress.')
                    self.call_required_fuctions(
                        required_actions = run_status.required_action.submit_tool_outputs.model_dump() 
                    )
                        
    def run_steps(self):
        run_steps = self.client.beta.threads.runs.steps.list(
            thread_id=self.thread_id,
            run_id=self.run.id
        )
        print(f'Run steps: {run_steps}')
            
manager = AssistantManager()
manager.create_assistant()