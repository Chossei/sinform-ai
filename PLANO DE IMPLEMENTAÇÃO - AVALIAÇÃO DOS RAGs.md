**AVALIAÇÃO DOS RAGS EXECUTADOS**

Este documento objetiva apresentar o plano metodológico para a construção de um pipeline automatizado a fim de avaliar a qualidade de cada método de RAG empregado.  Em resumo, o experimento seguinte consiste em verificar a taxa de acurácia dos RAGs com PDFs de todos os cursos de graduação da UFBA, a partir de classes pré-definidas com o modelo de classificação JEV para ditar se a resposta está coerente ou pouco coerente.

**CONSTRUÇÃO DA BASE DE DADOS: OS PDFs**

Na estrutura de arquivos atual, consta pastas para cada curso específico da UFBA.

1. Pesquise na internet os nomes dos 133 cursos existentes na universidade e seu formato (bacharelado ou licenciatura).
2. Crie oito pastas com as áreas de conhecimento seguindo a classificação: Ciências Exatas e da Terra, Ciências Biológicas, Engenharias, Ciências da Saúde, Ciências Agrárias, Ciências Sociais Aplicadas, Ciências Humanas e Linguística, Letras e Artes.
3. Crie uma pasta para cada curso que você encontrou inserindo-as em suas respectivas grandes áreas do conhecimento.

Agora, o objetivo será encontrar e baixar o maior número de pdfs existentes de cada curso, com informações atualizadas sobre o curso, regulamento, regras etc., presentes nos sites dos colegiados e dos departamentos. Crie uma pasta separada chamada “UFBA \- Geral” (ao lado das áreas de conhecimento) para armazenar os pdfs que não estiverem associados especificamente a um curso, como o REGPG.
Use subagentes para dividir e conquistar.

**O FATIAMENTO COM O PRÉ-LLM**

Após a etapa de downloads com os pdfs, sua tarefa será desenvolver um script para fatiar os pdfs a partir dos pré-llms. A mesma lógica de armazenamento de arquivos e fluxo de pipeline seguidos em C:\\Users\\choss\\OneDrive\\Documentos\\Aplicação \- Sinform AI\\FLUXO\_RAG\_DETALHADO.md para construção do banco vetorial de cada curso deve ser aplicada.
Verifique os scripts que já existem e adapte a cada curso, para criar suas respectivas pastas de pdfs fatiados, arquivos parquet e json.
As chaves de API estão disponíveis no arquivo .env, inclusive uma chave do gemini paga, denominada “GEMINI\_PAGO\_RICARDO”, para quando as requisições por dia das duas chaves gratuitas acabarem. Lembre-se de fazer requisições em paralelo para o modelo e de deixar o fallback para o gemini 3.1 flash lite. Para a chave paga, faça inferência flexível (metade do custo da API).

**CONJUNTO DE TESTES**

Para comparar o desempenho dos RAGs, será necessário desenvolver um conjunto de testes. Siga a estrutura de colunas do excel C:\\Users\\choss\\OneDrive\\Documentos\\Aplicação \- Sinform AI\\Experimento\\Conjunto de Testes.xlsx, incluindo ao lado a coluna “Curso”.
A coluna curso trará o curso selecionado para ser testado. Um novo fluxo de geração de perguntas deve ser elaborado via script. Serão 100 perguntas para cada curso, das quais as 100 serão divididas proporcionalmente para a quantidade de documentos baixados em cada curso. Crie uma lógica de cálculo para definir quantas perguntas serão selecionadas para cada documento. Para cada documento, uma chamada de modelo deve ser feita requisitando ao modelo a necessidade de criar “x” perguntas difíceis para avaliar a qualidade de um RAG. O modelo estará contextualizado via API File. O modelo deve retornar as “x” perguntas em output estruturado. As perguntas devem ir para o conjunto de testes, junto com o nome do documento e o curso da graduação.

**OS MÉTODOS DE RAG**

Quatro metodologias de RAG serão comparadas: RAG tradicional, RAG com fichamentos (consulta por embeddings), RAG  com fichamento (consulta pelo JEV), RAG com JEV.

(i) RAG tradicional: deve seguir o fluxo presente em C:\\Users\\choss\\OneDrive\\Documentos\\Aplicação \- Sinform AI\\Experimento\\instrucoes [adicionais.md](http://adicionais.md).

(ii) RAG com fichamentos (consulta por embeddings): deve seguir o fluxo presente em C:\\Users\\choss\\OneDrive\\Documentos\\Aplicação \- Sinform AI\\FLUXO\_RAG\_DETALHADO.md, no capítulo 4\.

(iii) RAG com fichamentos (consultas pelo JEV):  deve seguir o fluxo presente em C:\\Users\\choss\\OneDrive\\Documentos\\Aplicação \- Sinform AI\\Experimento\\experimento [adicional.md](http://adicional.md). (Por enquanto, não se preocupe em atualizar o streamlit, ainda que o documento diga).

(iv) **NOVO:** RAG com JEV.
O RAG com JEV consiste em utilizar o modelo Jev Type Search 1.14 via OpenRouter para selecionar os documentos que entrariam na janela de contexto gemini, que o modelo de decisão achar necessário (ou seja, sem utilizar embeddings). Neste sentido, será executada chamadas em paralelo para cada fichamento disponível do curso. Caso o JEV retorne TRUE para aquele fichamento, aquela fatia deve entrar na janela de contexto do modelo.

A instrução padrão do JEV será:
"Verifique se a informação que o usuário solicita pode estar presente no trecho do documento {nome do documento} de acordo com seu respectivo resumo.

Mensagem do usuário:
{mensagem do usuário}

Resumo do documento:
{resumo do documento}".

**OBSERVAÇÕES:** Para os três primeiros métodos, o experimento deve ser replicado para mudar o parâmetro k, de modo que teremos Top-1 fatiamentos, o Top-5 fatiamentos e o Top-10 fatiamentos a entrar na janela de contexto do modelo gemini. Na engenharia de prompt dos modelos, eles devem ser instruídos para serem objetivos, claros e breves em suas respostas. O parâmetro de reasoning deve estar configurado para o mínimo possível.

**Em resumo…**
Teremos 133 \* 100 chamadas com o pré-LLM que definirá com output estruturado o intervalo/quantidade de páginas, seus respectivos fichamentos para cada intervalo de páginas, e as perguntas que serão usadas no conjunto de testes. Antes de realizar a etapa do pré-LLM, rode o script para definir a quantidade de perguntas de cada documento.
Depois, no experimento, 3 \* 100 \* 3 chamadas (os três métodos de RAG) e 100 chamadas (RAG com JEV \- sem contar as chamadas do jev avaliador), totalizando 1000 chamadas por curso.

**O LLM JULGADOR**

Por fim, o LLM julgador também será o jev type search 1.14, diferenciando-se quanto à engenharia de prompt e a informação que ele receberá.
Para cada observação do conjunto de testes, o LLM receberá a pergunta do conjunto de teste, a resposta do gabarito e a resposta do rag. A instrução deve ser:
"Avalie se a resposta do modelo gerada via RAG condiz com o gabarito oficial para a pergunta apresentada.

PERGUNTA

RESPOSTA GABARITO

RESPOSTA MODELO".Na descrição das quatro categorias que o modelo deve escolher, defina:

- Incorreta: A resposta não contém nenhuma informação correta do gabarito.
- Parcialmente incorreta: A resposta contém apenas fragmentos mínimos de acerto, omitindo a maior parte das informações essenciais ou trazendo erros.
- Parcialmente correta: A resposta contém a maior parte das informações essenciais do gabarito, apresentando apenas omissões secundárias ou imprecisões leves.
- Correta: A resposta contempla todas as informações essenciais do gabarito de forma completa.



**EXTRA**

Para reestruturar o conjunto de testes, resultados, sugiro que inclua as seguintes colunas:

logprob_julgador_{categoria da decisao}: logprob de cada categoria do llm julgador. no total serão 4 colunas aqui.

decisao_julgador: categoria que o LLM julgador retornou no modelo.

top_k: o numero entre 1, 5, 10 ou Não se aplica (rag_fichamento_jev_livre)).

quantidade_documentos: quantidade de documentos que o rag_fichamento_jev_livre decidiu. (Não se aplica para os outros metodos)

metodo_rag: o metodo usado no rag (rag_tradicional, rag_fichamento_embedding, rag_fichamento_jev_topk, rag_fichamento_jev_livre).

custo_gemini: custo do uso do modelo gemini para responder.

custo_jev_consultas: custo do uso do modelo jev para fazer as consultas e decidir os fichamentos.

custo_jev_julgador: custo do uso do modelo jev para julgar a resposta do gemini.

Remova as colunas de probs de acerto do experimento anterior. Ou melhor: faça uma nova base de dados denominada "Resultados do teste". Lembre-se de incluir as colunas:

Documento, Curso, Pergunta, Gabarito, Resposta do modelo.
