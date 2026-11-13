"""
===============================================================================
MÓDULO CENTRAL DE ENGENHARIA DE PROMPT — AVALIAÇÃO DOS RAGs (UFBA)
===============================================================================
Este arquivo centraliza TODOS os prompts e instruções de modelos utilizados
no pipeline de fatiamento, geração de perguntas, execução dos RAGs e avaliação.

Você pode alterar livremente os textos, diretrizes, personas e regras abaixo
sem precisar modificar a lógica de execução dos scripts.
===============================================================================
"""

# =============================================================================
# 1. PRÉ-LLM: FATIAMENTO MULTIMODAL E FICHAMENTO DE DOCUMENTOS (PDF SLICING)
# =============================================================================
PRE_LLM_SLICING_PROMPT = """Você é um especialista em estruturação de documentos normativos e acadêmicos universitários (UFBA).
Sua missão é analisar visual e textualmente este documento oficial e dividi-lo em blocos lógicos contíguos e sequenciais (chunks).

DIRETRIZES DE FATIAMENTO:
1. Analise a densidade de conteúdo, tabelas, seções normativas e quebras de tópicos.
2. Defina os intervalos de páginas de forma que cada bloco contenha uma unidade de sentido completa (ex: um capítulo, uma resolução específica, uma tabela de pontuação).
3. Cubra absolutamente TODAS as páginas do documento, da página 1 até a última, sem saltos e sem sobreposições.
4. Para cada intervalo, elabore um FICHAMENTO TÉCNICO, objetivo, denso e detalhado (máximo 800 tokens):
   - Cite artigos, parágrafos, incisos, números de resoluções e datas.
   - Detalhe requisitos, prazos, fluxos processuais, percentuais e critérios de deferimento/indeferimento.
   - Seja conciso e exato. Evite introduções vazias.

Retorne estritamente o JSON estruturado conforme o esquema especificado.
"""

# =============================================================================
# 2. GERAÇÃO PROPORCIONAL DE PERGUNTAS DIFÍCEIS PARA O CONJUNTO DE TESTES
# =============================================================================
GENERATE_QUESTIONS_PROMPT_TEMPLATE = """Você é um avaliador rigoroso de sistemas de (RAG) da Universidade Federal da Bahia.
Com base no documento oficial em anexo ({nome_documento}), gere exatamente {quantidade_perguntas} perguntas desafiadoras e complexas.

DIRETRIZES PARA AS PERGUNTAS:
1. As perguntas devem ser difíceis, exigindo interpretação de regras específicas, exceções, prazos exatos, combinações de artigos ou condições para deferimento.
2. Evite perguntas genéricas ou que possam ser respondidas com conhecimento de senso comum.
3. Para cada pergunta, elabore uma RESPOSTA GABARITO oficial, completa, precisa e fundamentada exclusivamente no texto do documento, citando artigos e prazos relevantes.
4. Não invente informações. Toda resposta deve ter respaldo estrito no documento.
5. A RESPOSTA GABARITO deve ser breve, clara e objetiva.

Retorne as perguntas no formato estruturado especificado.
"""

# =============================================================================
# 3. GERADOR DE RESPOSTAS RAG (GEMINI 3.5 FLASH LITE)
# =============================================================================
# 6. Quando citar um documento, resolução ou artigo, insira o link respectivo em formato markdown para transformar o trecho em hiperlink. (OCULTADO/COMENTADO A PEDIDO DO USUÁRIO PARA NÃO CONFUNDIR O EXPERIMENTO)
RAG_GENERATOR_SYSTEM_PROMPT = """Você é o SinformUFBA, o assistente consultor de normas e regulamentos acadêmicos da UFBA.

DIRETRIZES DE RESPOSTA:
1. Seja estritamente objetivo, claro e breve. Vá direto ao ponto sem saudações prolixas ou rodeios.
2. Fundamente sua resposta EXCLUSIVAMENTE nos documentos normativos fornecidos no contexto.
3. Se a informação não estiver presente nos documentos fornecidos, responda com honestidade e brevidade: "Esta informação não consta nos documentos consultados."
4. Sempre que cabível, cite expressamente o nome do documento, resolução ou artigo de onde a informação foi extraída.
5. Mantenha um tom institucional, formal e didático.
"""

RAG_USER_PROMPT_TEMPLATE = """Pergunta do estudante:
{pergunta}

Responda com base estrita nos documentos normativos anexados."""

# =============================================================================
# 4. SELETOR DE CONTEXTO JEV (TYPESAFE/JEV-1.14 VIA DECISIONS API)
# =============================================================================
JEV_CONTEXT_SELECTOR_INSTRUCTIONS = """Verifique se a informação que o usuário solicita pode estar presente no trecho do documento {nome_documento} de acordo com seu respectivo resumo.

Mensagem do usuário:
{mensagem_usuario}

Resumo do documento:
{resumo_documento}
"""

# =============================================================================
# 5. LLM JULGADOR (TYPESAFE/JEV-1.14 COMO JUIZ CLASSIFICADOR EM 4 NÍVEIS)
# =============================================================================
JEV_JUDGE_INSTRUCTIONS = "Avalie se a resposta do modelo gerada via RAG condiz com o gabarito oficial para a pergunta apresentada."

JEV_JUDGE_STATE_TEMPLATE = """PERGUNTA
{pergunta}

RESPOSTA GABARITO
{resposta_gabarito}


RESPOSTA MODELO
{resposta_modelo}
"""

JEV_JUDGE_CATEGORIES = {
    "Incorreta": "A resposta não contém nenhuma informação correta do gabarito.",
    "Parcialmente incorreta": "A resposta contém apenas fragmentos mínimos de acerto, omitindo a maior parte das informações essenciais ou trazendo erros.",
    "Parcialmente correta": "A resposta contém a maior parte das informações essenciais do gabarito, apresentando apenas omissões secundárias ou imprecisões leves.",
    "Correta": "A resposta contempla todas as informações essenciais do gabarito de forma completa."
}
