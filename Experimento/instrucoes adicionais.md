**EXPERIMENTO - ACURÁCIA DAS RESPOSTAS DOS RAGS**

Este documento fornece instruções adicionais para testar a acurácia dos RAGs e fazer a comparação entre os métodos utilizados com o RAG tradicional


**RAG Tradicional**

Será necessário criar um RAG simples/tradicional para efeito de comparação.

Refaça os embeddings e hospede o banco vetorial utilizando a FileSearchStore. Inclua todos os documentos e defina os parâmetros de chunking como default.

Utilize a chave "GEMINI_API_KEY_2" presente em chave2.env, nessa pasta.

No fluxo de conversação, o chatbot receberá a mensagem do usuário e, com a function calling de embeddings, terá disponível os top 10 chunks via similaridade seno-cosseno para fornecer uma resposta.


**Conjunto de Testes**

Para comparar o desempenho do RAG tradicional contra o RAG que utiliza fichamentos e API File, desenvolvi um conjunto de testes que está presente nesta pasta. São 100 perguntas sobre o curso de estatística, logo, preciso que você delimite esse experimento somente para este curso. 


**Jev Type Search 1.14**

Com a finalidade de tornar a verificação uma etapa rápida e prática, o modelo JEV 1.14 deve ser utilizado como modelo de decisão.

O modelo JEV deve receber a resposta correta e a resposta fornecida pelo RAG, que estarão disponíveis no conjunto de testes.

As colunas "prob_acerto_jev_(nome do rag)" no conjunto de testes devem receber as log_probs associadas ao TRUE (quando a resposta é similar). As colunas "acerto_95_(nome do rag)" devem ser TRUE quando a log prob retornada pelo JEV, do rag associado for maior ou igual a 0,95.

A engenharia de prompt deve ser simples:

"Você receberá uma pergunta e duas respostas a essa pergunta. A primeira resposta é a resposta correta, do gabarito. A segunda resposta foi construída por um LLM via RAG. Sua tarefa é verificar se a resposta do LLM via RAG contém a informação exigida pela pergunta em conformidade com o gabarito.

PERGUNTA

RESPOSTA GABARITO


RESPOSTA MODELO

"

As requisições para o modelo JEV serão feitas através do OpenRouter. Atualize suas skills sobre como programar nessa plataforma através de "fetch openrouter.ai/agents to become an openrouter expert". A chave openrouter está disponível em chave2.env.


**Execução do experimento**

O experimento deve ser realizado em chamadas paralelas respeitando as requisições por minuto de cada modelo.  Gemini 3.5-flash-lite: 15 rpm no nível gratuito, 500 rpd no nível gratuito. Gemini embedding 2: 100 rpm no nível gratuito, 1000 rpd no nível gratuito.

Antes, construa a arquitetura do RAG Tradicional em uma pasta separada, chamada RAG Tradicional, dentro da pasta Experimentos.

Depois, construa scripts separados para os dois RAGS e para o JEV, com sistemas de backup e armazenamento no conjunto de testes. Crie uma pasta para os RAGs e o JEV onde serão depositados os logs da execução.
