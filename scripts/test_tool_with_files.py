import os
from dotenv import load_dotenv
load_dotenv()
from google import genai
from google.genai import types

client = genai.Client()

# Testar se generate_content com FunctionCall manual ou chat permite passar files
print("Testando capacidade de associar files a respostas de tools...")
