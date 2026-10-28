import os
from dotenv import load_dotenv
load_dotenv()
from google import genai
from google.genai import types

client = genai.Client()

def test_manual_tool_with_uploaded_file():
    # Definição da função para a Tool
    def consultar_normas_academicas(duvida_especifica: str) -> dict:
        """Consulta as normas acadêmicas no banco de dados vetorial."""
        return {"status": "ok"}

    # 1. Chamada inicial do usuário
    user_msg = "Como funciona o trancamento de TCC?"
    print("Enviando pergunta inicial...")
    
    resp1 = client.models.generate_content(
        model="models/gemini-3.5-flash-lite",
        contents=user_msg,
        config=types.GenerateContentConfig(
            tools=[types.Tool(function_declarations=[
                types.FunctionDeclaration(
                    name="consultar_normas_academicas",
                    description="Consulta as normas, resoluções e regulamentos acadêmicos do curso.",
                    parameters=types.Schema(
                        type=types.Type.OBJECT,
                        properties={
                            "duvida_especifica": types.Schema(
                                type=types.Type.STRING,
                                description="Termo de pesquisa detalhado para buscar nos regulamentos."
                            )
                        },
                        required=["duvida_especifica"]
                    )
                )
            ])],
            temperature=0.1
        )
    )

    print("Function calls detectadas:", len(resp1.function_calls or []))
    if resp1.function_calls:
        fc = resp1.function_calls[0]
        print(f"Chamou {fc.name} com args {fc.args}")
        
        # Simular upload de um pedaço fatiado
        pdf_path = "Estatística (Bacharel)/Instrucao_Normativa_006_2025_Trancamento_TCC/Instrucao_Normativa_006_2025_Trancamento_TCC_paginas_1-2.pdf"
        uploaded_file = client.files.upload(file=pdf_path)
        print("Arquivo fatiado uploaded:", uploaded_file.name)
        
        # Montar histórico:
        # 1. User
        c1 = types.Content(role="user", parts=[types.Part.from_text(text=user_msg)])
        # 2. Model (FunctionCall)
        c2 = resp1.candidates[0].content
        # 3. User (FunctionResponse + Uploaded File)
        func_resp = types.Part.from_function_response(
            name=fc.name,
            response={"mensagem": "Top-10 fragmentos recuperados. Analise os documentos PDF fatiados anexos para fundamentar a resposta com artigos e páginas exatas."}
        )
        c3 = types.Content(role="user", parts=[
            func_resp,
            types.Part.from_uri(file_uri=uploaded_file.uri, mime_type="application/pdf")
        ])

        print("Enviando segunda etapa com o arquivo fatiado...")
        resp2 = client.models.generate_content(
            model="models/gemini-3.5-flash-lite",
            contents=[c1, c2, c3],
            config=types.GenerateContentConfig(
                temperature=0.15
            )
        )
        print("\nResposta Final Grounded:")
        print(resp2.text)

if __name__ == "__main__":
    test_manual_tool_with_uploaded_file()
