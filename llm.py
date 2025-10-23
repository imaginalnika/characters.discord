import json
import os
from dotenv import load_dotenv
from anthropic import Anthropic
from openai import OpenAI

load_dotenv(os.path.expanduser('~/.env'))

client = Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

def chat_response(chat_messages, system=None, schema=None):
    if schema:
        messages = chat_messages.copy()
        if system:
            messages.insert(0, {"role": "system", "content": system})
        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            response_format={"type": "json_schema", "json_schema": {"name": "response", "strict": True, "schema": schema}}
        )
        return json.loads(response.choices[0].message.content)
    else:
        kwargs = {"model": "claude-sonnet-4-5", "max_tokens": 8192, "messages": chat_messages}
        if system:
            kwargs["system"] = system
        response = client.messages.create(**kwargs)
        return response.content[0].text

def llm(prompt, system=None, schema=None):
    return chat_response([{"role": "user", "content": prompt}], system=system, schema=schema)
