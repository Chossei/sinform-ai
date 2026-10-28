import os
from dotenv import load_dotenv
load_dotenv()
from google import genai
from google.genai import types

client = genai.Client()

def test_tool_with_files():
    # 1. Definir função de tool
    def buscar_documentos(consulta: str) -> dict:
        return {
            "status": "sucesso",
            "documentos": ["Resolucao_03_2025"],
            "paginas": [1, 2],
            "resumo": "Regras de atividades complementares: max 200h, envio pelo SIGAA."
        }

    # 2. Primeira chamada com tool
    resp1 = client.models.generate_content(
        model="models/gemini-3.5-flash-lite",
        contents="Quais as regras de atividades complementares no curso de Estatística?",
        config=types.GenerateContentConfig(
            tools=[buscar_documentos],
            temperature=0.1
        )
    )

    print("Chamadas de função recebidas:", len(resp1.function_calls or []))
    for fc in (resp1.function_calls or []):
        print("Function call:", fc.name, fc.args)

    if resp1.function_calls:
        # Simular upload de um arquivo fatiado pequeno
        pdf_path = "Estatística (Bacharel)/Instrucao_Normativa_006_2025_Trancamento_TCC/Instrucao_Normativa_006_2025_Trancamento_TCC_paginas_1-2.pdf"
        uploaded = client.files.upload(file=pdf_path)
        print("Uploaded file:", uploaded.uri)

        # Montar segunda chamada
        # Turno 1: User
        # Turno 2: Model (FunctionCall)
        # Turno 3: User/FunctionResponse + File
        user_content = types.Content(role="user", parts=[types.Part.from_text(text="Quais as regras de atividades complementares no curso de Estatística?")])
        model_call_content = resp1.candidates[0].content
        
        func_resp_part = types.Part.from_function_response(
            name="buscar_documentos",
            response={
                "mensagem": "10 documentos recuperados com sucesso para fundamentação.",
                "fichamentos": [
                    {"doc": "Resolucao_03_2025", "paginas": "[1, 2]", "resumo": "Regras de atividades complementares."}
                ]
            }
        )
        
        # Enviar tanto a resposta da função quanto o arquivo multimodal
        tool_content = types.Content(
            role="user",
            parts=[
                func_resp_part,
                types.Part.from_uri(file_uri=uploaded.uri, mime_type="application/pdf")
            ]
        )

        resp2 = client.models.generate_content(
            model="models/gemini-3.5-flash-lite",
            contents=[user_content, model_call_content, tool_content],
            config=types.GenerateContentConfig(
                temperature=0.2
            )
        )
        print("Resposta final gerada com sucesso:")
        print(resp2.text[:300])

if __name__ == "__main__":
    test_tool_with_files()
