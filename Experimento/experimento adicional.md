Este documento foi desenvolvido para incluir mais um campo de experimentação no RAG.

O foco agora será utilizar o JEV 1.14 em substituição ao embedding para definir os pdfs que serão enviados como contexto ao modelo.

A estrutura do RAG permanece a mesma: utilize os fatiamentos de pdf que já existem, com os fichamentos já produzidos.

O fluxo do RAG permanece apenas com uma alteração: quando o modelo receber a mensagem do usuário, ele deverá ter a possibilidade de utilizar a function calling de consultar ao jev para retornar os pdfs fatiados na API File. O JEV deve receber, na engenharia de prompt, a pergunta do usuário e, logo abaixo, o nome do documento e seu respectivo fichamento.

Instrução: "Verifique se a informação que o usuário solicita pode estar presente no documento {nome do documento} de acordo com seu respectivo resumo: {resumo do documento}".

O modelo deve usar a escolha booleana. Um algoritmo deve ser criado para selecionar os top-10 fichamentos em que o JEV retornou TRUE a partir da log-probabilidade emitida (top 10 maiores log-probabilidades). Os 10 pdfs associados ao fichamento, então, são enviados para o modelo.

A partir desse novo fluxo, refaça o experimento e inclua as novas colunas no conjunto de testes. Lembre-se de fazer requisições em paralelo e respeitar as RPM e RPD de cada modelo.

Atualize a estrutura do dashboard streamlit do SinformAI para acomodar esses novos resultados.
