# -*- coding: utf-8 -*-
"""
Gera o conjunto de testes de 200 perguntas (Experimento/Conjunto de Testes 200.xlsx)
a partir do sorteio de 400 perguntas (Experimento/backups/grupos_hibridas_brutos.json):
- 100 perguntas únicas (1 PDF)
- 50 perguntas híbridas de 2 PDFs (sintetizadas de 50 pares = 100 perguntas originais)
- 50 perguntas híbridas de 3 PDFs (sintetizadas de 50 trincas = 150 perguntas originais)

Todas as 200 perguntas foram revisadas manualmente para remover qualquer referência
a documentos, resoluções, artigos, parágrafos, anexos, PPCs, manuais, catálogos,
fluxogramas, ementas ou atas, mantendo apenas as perguntas brutas.
"""

import json
import os
import re
import shutil
import pandas as pd

# ==============================================================================
# REVISÃO MANUAL DAS 100 PERGUNTAS ÚNICAS (Q001 A Q100) SEM REFERÊNCIA A DOCUMENTOS
# ==============================================================================
UNICAS_OVERRIDES = {
    "Q001": {
        "Pergunta": "No curso de Sistemas de Informação da UFBA, quais são as duas informações obrigatórias que devem acompanhar as solicitações de dilatação do prazo máximo para integralização curricular, e o que o plano de atividades deve detalhar especificamente?"
    },
    "Q003": {
        "Pergunta": "No Centro de Pesquisa em Geofísica e Geologia (CPGG), como são designados os Chefes dos Setores de Apoio Técnico e Administrativo e de Apoio de Informática?"
    },
    "Q004": {
        "Pergunta": "No Instituto de Psicologia da UFBA, como são definidos os Núcleos Acadêmicos em termos de estrutura, flexibilidade e instâncias de deliberação para sua criação, composição e extinção?"
    },
    "Q005": {
        "Pergunta": "Qual é o grau acadêmico do curso de Educação Física oferecido pela Faculdade de Educação da UFBA?"
    },
    "Q006": {
        "Pergunta": "No curso de Letras Vernáculas com Língua Estrangeira Moderna da UFBA, qual é a antecedência mínima para a convocação das reuniões ordinárias do Colegiado e o que deve obrigatoriamente constar na convocação?"
    },
    "Q011": {
        "Pergunta": "Quais são as disciplinas obrigatórias que compõem o 5º semestre do Bacharelado em Ciências Sociais da UFBA?"
    },
    "Q012": {
        "Pergunta": "No SIGAA, quais são as formas de autenticação exigidas sempre que uma alteração é realizada na solicitação de matrícula e qual procedimento final garante a comprovação de que o processo foi concluído?"
    },
    "Q013": {
        "Pergunta": "Qual é a carga horária total exigida para a integralização do curso de Artes Plásticas da Escola de Belas Artes da UFBA?"
    },
    "Q015": {
        "Pergunta": "No curso de Desenho e Plástica da UFBA, o estudo mais aprofundado das formas geométricas do plano e suas aplicações em problemas reais pertence a qual disciplina do 2º período?"
    },
    "Q017": {
        "Pergunta": "Quais conteúdos e práticas compõem o estudo da disciplina 'Libras I - Língua Brasileira de Sinais Nível I' (LET E48) na UFBA?"
    },
    "Q018": {
        "Pergunta": "No curso de Estatística da UFBA, qual é o prazo mínimo de antecedência com que o orientador deve providenciar a entrega de cópias do projeto ou trabalho monográfico de TCC à banca examinadora?"
    },
    "Q020": {
        "Pergunta": "Na Escola de Teatro da UFBA, quais são as vedações aplicadas aos docentes não integrantes da carreira do Magistério Superior que compõem os Departamentos?"
    },
    "Q021": {
        "Pergunta": "Em quais turnos são ofertados os cursos de graduação em Química no Instituto de Química da UFBA?"
    },
    "Q022": {
        "Pergunta": "Quais são as atividades práticas e abordagens teóricas realizadas na disciplina GEDC 0042 (Estágio Supervisionado em Ensino de Artes Visuais I) no 5º período?"
    },
    "Q023": {
        "Pergunta": "Qual unidade acadêmica da UFBA abriga os cursos de graduação em Química?"
    },
    "Q024": {
        "Pergunta": "Nas discussões de reforma curricular do Núcleo Docente Estruturante em abril de 2020, para qual carga horária foi proposta a redução das disciplinas de Economia, Administração e Legislação, e quais limites percentuais de carga horária EAD da UFBA e do MEC foram comparados?",
        "Resposta Gabarito": "Foi proposta a redução para 34 horas das disciplinas de Economia, Administração e Legislação, além da criação de disciplinas comuns (Introdução à Engenharia e Metodologia Científica) e redução de carga horária em Cálculo A, B e C mantendo os conteúdos. Quanto à modalidade EAD em cursos presenciais, comparou-se o limite interno da UFBA de até 20% da carga horária total com a portaria do MEC de 2019 que permite até 40%."
    },
    "Q025": {
        "Pergunta": "Qual é o código, o total de créditos e a carga horária de Teoria (T), Prática (P) e Estágio (E), respectivamente, da disciplina Introdução à Computação Gráfica na UFBA?"
    },
    "Q026": {
        "Pergunta": "Qual é o campus de funcionamento dos cursos de Química do Instituto de Química da UFBA?"
    },
    "Q028": {
        "Pergunta": "No Bacharelado Interdisciplinar em Artes da UFBA, quais são os três critérios utilizados pelo Colegiado para analisar e validar as Atividades Complementares dos estudantes?"
    },
    "Q029": {
        "Pergunta": "Nos cursos da Escola de Belas Artes da UFBA, qual disciplina do 5º período aborda a estrutura facial, suas características, simplificação e interpretação tendo a figura humana como ponto de referência?"
    },
    "Q031": {
        "Pergunta": "Nos cursos de Desenho e Plástica e Artes Plásticas da Escola de Belas Artes da UFBA, quantas horas totalizam o 6º semestre do curso?"
    },
    "Q033": {
        "Pergunta": "Qual é o turno associado à oferta anual de 16 vagas via BI-CPL no curso de Química da UFBA?"
    },
    "Q035": {
        "Pergunta": "Entre os cursos de Estudos de Gênero e Diversidade, Filosofia e História da Faculdade de Filosofia e Ciências Humanas da UFBA, qual funciona no turno Noturno?"
    },
    "Q036": {
        "Pergunta": "Qual é a unidade acadêmica responsável pela oferta dos cursos de graduação em Química na UFBA?"
    },
    "Q038": {
        "Pergunta": "Qual é o objeto de estudo da disciplina 'Perspectiva' (ARQ 010), ofertada no 5º período para os cursos da Escola de Belas Artes da UFBA?"
    },
    "Q039": {
        "Pergunta": "Quantas vagas anuais via SISU e via BI-CPL são ofertadas para o curso de Fonoaudiologia da UFBA e qual é o e-mail oficial de contato do colegiado?",
        "Resposta Gabarito": "Para o curso de Fonoaudiologia (Bacharelado, turno diurno, Campus Salvador - Canela) são ofertadas anualmente 48 vagas via SISU e 12 vagas via BI-CPL, sendo o e-mail de contato oficial colefono@ufba.br."
    },
    "Q044": {
        "Pergunta": "Qual é a soma total da oferta anual de vagas via BI-CPL somando os cursos de Estudos de Gênero e Diversidade, Filosofia e História da UFBA?"
    },
    "Q046": {
        "Pergunta": "Qual é o total somado de vagas anuais oferecidas pelo SISU nos três cursos de graduação da Escola de Administração da UFBA (Administração, Administração Pública e Gestão Social e Secretariado Executivo)?"
    },
    "Q050": {
        "Pergunta": "No curso de Engenharia de Transportes da UFBA, qual disciplina obrigatória aborda de forma específica os temas transversais relativos à Educação Ambiental?"
    },
    "Q052": {
        "Pergunta": "No SIGAA, qual é a recomendação essencial ao utilizar a tela de filtro para buscar turmas abertas de outros cursos (componentes livres)?"
    },
    "Q053": {
        "Pergunta": "Quais são as atribuições formais de ensino designadas ao licenciado em História pela UFBA?"
    },
    "Q055": {
        "Pergunta": "Qual é a unidade acadêmica responsável, a carga horária teórica e o pré-requisito obrigatório da disciplina Álgebra Linear A (código MAT A07) na UFBA?"
    },
    "Q056": {
        "Pergunta": "Qual é a área acadêmica geral da UFBA que abrange a Escola de Belas Artes e a Escola de Dança?"
    },
    "Q058": {
        "Pergunta": "Na organização dos cursos de graduação da UFBA, qual é o limite percentual máximo em que a carga horária de um curso pode ultrapassar a carga horária nacional média das IFES?"
    },
    "Q062": {
        "Pergunta": "No Bacharelado em Ciências Sociais da UFBA, quais são os formatos possíveis para o Trabalho de Conclusão de Curso (TCC) e qual exigência adicional existe para os formatos não monográficos?"
    },
    "Q064": {
        "Pergunta": "No Bacharelado em Ciência da Computação da UFBA, quais são as três formas pelas quais o aluno pode ser orientado a cursar os componentes curriculares optativos?"
    },
    "Q068": {
        "Pergunta": "A qual Área do Conhecimento da UFBA pertencem os cursos de Ciências Econômicas, Educação Física e Educação do Campo?"
    },
    "Q069": {
        "Pergunta": "Quais são os canais digitais oficiais da SUPAC (Superintendência Acadêmica da UFBA) para acompanhamento de notícias e informações acadêmicas atualizadas?"
    },
    "Q073": {
        "Pergunta": "Qual é o campus do curso de Dança noturno na Escola de Dança da UFBA?"
    },
    "Q074": {
        "Pergunta": "No processo de solicitação de matrícula ou flexibilização de pré-requisito no SIGAA, por que motivo é fundamental emitir e salvar o comprovante ao final da submissão?"
    },
    "Q075": {
        "Pergunta": "No curso de Ciências Biológicas do IMS/UFBA, como é decidido o desempate na inscrição em componentes curriculares quando há conflito de prioridades iguais no escalonamento?"
    },
    "Q077": {
        "Pergunta": "No Bacharelado Interdisciplinar em Artes da UFBA, quais são as siglas das unidades de ensino classificadas na subárea de 'Cultura Humanística'?"
    },
    "Q079": {
        "Pergunta": "Qual é a oferta anual de vagas via SISU para o curso de Saúde Coletiva da UFBA?"
    },
    "Q082": {
        "Pergunta": "Qual é o total de vagas anuais oferecidas via SISU para o curso de Ciências Contábeis da UFBA somando ambos os turnos?"
    },
    "Q089": {
        "Pergunta": "No Bacharelado em Ciências Sociais da UFBA, quais são os tempos mínimo e máximo de integralização em semestres e qual é o limite máximo de estudantes por docente orientador na orientação acadêmica?",
        "Resposta Gabarito": "O tempo de integralização do Bacharelado em Ciências Sociais é de no mínimo 8 semestres e no máximo 12 semestres (permitida dilatação de prazo de até 50%). Na orientação acadêmica, os grupos possuem o limite de até 10 estudantes por docente orientador, com encontros semanais."
    },
    "Q090": {
        "Pergunta": "Quem foi eleito Vice-Coordenador do Colegiado do Curso de Engenharia da Computação da UFBA para o biênio 2016/2018 (com início em 21 de setembro de 2016) e por quantos votos favoráveis?"
    },
    "Q092": {
        "Pergunta": "No Instituto de Biologia da UFBA, qual dispositivo normativo interno foi invocado pela professora Cláudia ao declarar abstenção na votação para aprovação das disciplinas do mestrado em 2017?"
    },
    "Q093": {
        "Pergunta": "Na Escola de Teatro da UFBA, o Núcleo de Apoio aos Laboratórios Cênicos é responsável pela administração e manutenção de quais instalações específicas?"
    },
}

# ==============================================================================
# 50 PERGUNTAS HÍBRIDAS DE 2 PDFS (Q101 A Q150) — BRUTAS, SEM REFERÊNCIA A DOCS
# ==============================================================================
HIBRIDAS_2PDFS = {
    "H2_01": {
        "Pergunta": "Quantas vagas anuais via BI-CPL são ofertadas para o curso de Estudos de Gênero e Diversidade da UFBA e quais são os requisitos de vínculo, carga horária semanal e Coeficiente de Rendimento exigidos de bolsistas do PIBIC em Ciências Sociais?",
        "Resposta Gabarito": "Para o curso de Estudos de Gênero e Diversidade são ofertadas 10 vagas anuais via BI-CPL. Já para ser bolsista do PIBIC, exige-se não possuir vínculo empregatício, dedicar 20 horas semanais à pesquisa e apresentar Coeficiente de Rendimento (CR) superior a 5,0."
    },
    "H2_02": {
        "Pergunta": "No curso de Artes Plásticas da UFBA, qual é a carga horária prevista para o 3º semestre e qual é o objetivo e campo de atuação da disciplina 'Metodologia do Ensino das Artes Visuais' (EDC J26) no 4º período?",
        "Resposta Gabarito": "A carga horária prevista para o 3º semestre é de 435 horas. Na disciplina EDC J26 (4º período), o objetivo e campo de atuação compreendem o planejamento de práticas de ensino das artes visuais, sua implementação em espaços não-formais de ensino e a elaboração e aplicação de projetos para o ensino das artes visuais."
    },
    "H2_03": {
        "Pergunta": "Como se divide a carga horária total de 2.400 horas do Bacharelado Interdisciplinar em Ciência e Tecnologia e qual é a carga horária máxima total permitida para Atividades Complementares nos Bacharelados Interdisciplinares do IHAC?",
        "Resposta Gabarito": "No BI em Ciência e Tecnologia, as 2.400 horas totais dividem-se em 1.924 horas de componentes curriculares e Atividades Complementares e 476 horas de componentes de livre escolha, exigindo-se o mínimo de 360 horas de Atividades Complementares (Eixo Integrador). Nos Bacharelados Interdisciplinares do IHAC, a carga horária máxima total exigida e permitida para Atividades Complementares é exatamente de 360 horas."
    },
    "H2_04": {
        "Pergunta": "No curso de Biotecnologia do IMS/UFBA, como se procede caso ocorra um novo pedido de vista em processo no Colegiado após o primeiro prazo e em que data ocorre a divulgação dos resultados da Matrícula WEB SIGAA para 2026.1?",
        "Resposta Gabarito": "Havendo novo pedido de vista após o primeiro prazo, ele é concedido simultaneamente a todos os membros que solicitarem, e pedidos subsequentes dependem de aprovação prévia do plenário do Colegiado. A divulgação dos resultados da Matrícula WEB SIGAA para 2026.1 ocorre em 03/03/2026."
    },
    "H2_05": {
        "Pergunta": "No Bacharelado em Ciência da Computação da UFBA, qual é o departamento responsável, a carga horária e a equivalência da disciplina MAT236 (Métodos Estatísticos), e qual é a duração máxima permitida para a apresentação oral do TCC?",
        "Resposta Gabarito": "A disciplina MAT236 (Métodos Estatísticos) pertence ao Departamento de Estatística, tem carga horária 68/00/00 e equivale à antiga MATA96. Já a apresentação oral do TCC tem duração máxima permitida de 20 (vinte) minutos."
    },
    "H2_06": {
        "Pergunta": "Em Ciências Biológicas do IMS/UFBA, o que ocorre administrativamente caso o mandato como membro do colegiado de um docente que exerce a função de Coordenador não possa ser renovado, e como o SIGAA contabiliza a carga horária excedente de componentes optativos?",
        "Resposta Gabarito": "Garante-se ao Coordenador finalizar o exercício de seu mandato por um período máximo de um ano mesmo que seu mandato como membro não possa ser renovado, mantendo-se provisoriamente a composição ampliada em um membro. Já o excedente de componentes optativos cursados no SIGAA é convertido em carga horária de componente livre, permitindo cursar até 60h extras."
    },
    "H2_07": {
        "Pergunta": "No curso de Ciências Biológicas do IMS/UFBA, qual é o dever de um membro do Colegiado impedido de comparecer a uma reunião agendada e qual é a ordem de prioridade para a inscrição de estudantes em Componentes Optativos?",
        "Resposta Gabarito": "O membro titular impedido deve convocar seu suplente para comparecer à reunião. A ordem de prioridade para inscrição em componentes optativos é: 1º semestralizados e retornando de mobilidade; 2º formandos; 3º reprovados ou que trancaram a disciplina; 4º quem deseja antecipar componentes curriculares."
    },
    "H2_08": {
        "Pergunta": "No curso de Design da UFBA, qual componente curricular do 3º semestre corresponde ao código EBA 003 e qual é a finalidade formativa da disciplina Instituição de Direito Público e Privado (DIR 159)?",
        "Resposta Gabarito": "No 3º semestre de Design, o código EBA 003 refere-se ao componente História da Arte III, de 90 horas (EBA A86). Já a disciplina DIR 159 tem por finalidade oferecer visão dos instrumentos jurídicos utilizados nas atividades econômica, administrativa e arquivística, abordando Estado, Constituição, ordem econômica, domínio público, pessoas e objeto de direito e contratos."
    },
    "H2_09": {
        "Pergunta": "No Instituto de Biologia da UFBA, quais nomes foram indicados para compor a comissão de avaliação do cargo de biólogo/Genética em janeiro de 2014 e por qual motivo o protocolo para registro de estágio encaminhado pelo Nupex foi retirado de pauta em 2017?",
        "Resposta Gabarito": "Para a comissão de biólogo/Genética em 09/01/2014, foram indicados: Eduardo Rego (UNEB), Suzi (UEFS), Rosalia (UEFS), Ana Maria Valtsmith (UESB) e Fernanda Gaioto (UESB). Já o ponto sobre o protocolo de registro de estágio do Nupex foi retirado de pauta porque a plenária manifestou interesse em receber o texto previamente para avaliação detalhada."
    },
    "H2_10": {
        "Pergunta": "Em Engenharia Civil na UFBA, qual é o pré-requisito e o semestre de início de vigência da disciplina ENGR55 (Tópicos Especiais de Concreto Estrutural), e quais motivos justificam o deferimento de Avaliação de Conhecimento Prévio (ACP) dentro e fora do prazo de 25% do semestre letivo?",
        "Resposta Gabarito": "Para ENGR55 (Tópicos Especiais de Concreto Estrutural), o pré-requisito para o curso 102 é ENG118, com vigência a partir de 2024-1. Justificam o pedido de ACP pelo Colegiado (CCEC): aprovação em concurso público com nomeação, aprovação em pós-graduação stricto sensu comprovada ou situações equivalentes aprovadas pelo Colegiado; fora do prazo de 25% do início do semestre, exige-se motivo comprovado (concurso, contratação ou mudança de Estado) e deliberação prévia do Colegiado."
    },
    "H2_11": {
        "Pergunta": "Em Engenharia Mecânica na UFBA, quais são os códigos exatos das disciplinas exigidas como pré-requisitos obrigatórios para ENG-003 (Eletricidade) e para ENG-037 (Planejamento e Controle da Produção)?",
        "Resposta Gabarito": "Para a matrícula em ENG-003 (Eletricidade), o pré-requisito obrigatório é FIS-123 (Física Geral e Exp. III-E). Para a matrícula em ENG-037 (Planejamento e Controle da Produção), os três pré-requisitos obrigatórios são ENG-D04 (Métodos Matemáticos e Computacionais em Engenharia), ENG-372 (Princípios dos Processos Químicos) e ENG-D02 (Estatística na Engenharia)."
    },
    "H2_12": {
        "Pergunta": "Em Engenharia de Produção na UFBA, qual é a carga horária total, o número de créditos e o ano de aprovação da disciplina FCC 024 (Contabilidade de Custos), e qual é o único pré-requisito obrigatório para cursar ENG-003 (Eletricidade)?",
        "Resposta Gabarito": "A disciplina FCC 024 (Contabilidade de Custos) possui 68 horas de carga horária total, 3 créditos e foi aprovada em 2006. Já a disciplina ENG-003 (Eletricidade) exige como único pré-requisito obrigatório ter cursado FIS-123 (Física Geral e Exp. III-E)."
    },
    "H2_13": {
        "Pergunta": "Quantas vagas anuais e em qual turno são oferecidas para o curso de Farmácia no Campus Anísio Teixeira (IMS), e qual é o limite percentual máximo de carga horária a distância permitido em cursos presenciais de graduação e pós-graduação stricto sensu da UFBA?",
        "Resposta Gabarito": "Para o curso de Farmácia no Campus Anísio Teixeira (IMS), são oferecidas anualmente 45 vagas no turno diurno. Já a oferta na modalidade a distância em cursos presenciais de graduação e pós-graduação stricto sensu da UFBA não pode ultrapassar 20% (vinte por cento) da carga horária total do curso."
    },
    "H2_14": {
        "Pergunta": "Como se compõe a representação docente, técnico-administrativa e estudantil na Congregação do Instituto de Geociências (IGEO) e quais são os quatro segmentos que integram o Conselho Deliberativo do Centro de Pesquisa em Geofísica e Geologia (CPGG)?",
        "Resposta Gabarito": "Na Congregação do IGEO, há representantes docentes (sendo um de cada classe), 2 representantes dos Servidores Técnico-Administrativos e representantes estudantis na proporção definida em lei. No Conselho Deliberativo do CPGG, os quatro segmentos são: I - diretores dos Institutos de Geociências e de Física (ou representantes); II - Coordenador e Coordenador Adjunto do CPGG; III - um representante dos pesquisadores; IV - representantes discentes na forma da lei."
    },
    "H2_15": {
        "Pergunta": "Quais são os quatro Departamentos que correspondem aos cursos de graduação do Instituto de Geociências (IGEO) e por quais cargos é exercida e integrada a Coordenação do Centro de Pesquisa em Geofísica e Geologia (CPGG)?",
        "Resposta Gabarito": "No IGEO, os quatro Departamentos são: I - Geologia, II - Geografia, III - Geofísica e IV - Oceanografia. No CPGG, a Coordenação (órgão de execução, integração e fiscalização) é exercida pelo Coordenador, apoiado por um Coordenador Adjunto e pelos Chefes de Programas."
    },
    "H2_16": {
        "Pergunta": "Como são eleitos o Coordenador e o Coordenador Adjunto do Centro de Pesquisa em Geofísica e Geologia (CPGG) e qual é a condição exigida para que requerimentos administrativos tramitem no Instituto de Geociências (IGEO)?",
        "Resposta Gabarito": "No CPGG, o Coordenador e o Coordenador Adjunto são eleitos pelo Conselho Deliberativo por votação secreta em sessão especial, a partir de listas tríplices encaminhadas pelo Conselho Científico. No IGEO, os requerimentos administrativos somente tramitam quando estiverem devidamente instruídos."
    },
    "H2_17": {
        "Pergunta": "Como são alocados as disciplinas e os demais componentes curriculares ministrados pelo Instituto de Geociências (IGEO), e quais são as três competências atribuídas ao Chefe de Programa no Centro de Pesquisa em Geofísica e Geologia (CPGG)?",
        "Resposta Gabarito": "No IGEO, as disciplinas são alocadas nos Departamentos e os demais componentes curriculares nos respectivos Colegiados de Curso. No CPGG, compete ao Chefe de Programa: I - supervisionar a execução dos projetos e relatórios de progresso, estimulando a produção científica; II - estruturar equipes ou grupos de pesquisa, propondo nomes de pesquisadores ao Conselho Científico; III - administrar os laboratórios do CPGG vinculados ao Programa."
    },
    "H2_18": {
        "Pergunta": "Na Escola de Música da UFBA, o que o estudante deve fazer no SIGAA se a busca por turmas abertas de outros cursos retornar uma quantidade excessiva de turmas, e qual docente e carga horária estão atribuídos à turma T01 de MUSC12 (Composição Suplementar I)?",
        "Resposta Gabarito": "Caso a busca retorne quantidade excessiva de turmas no SIGAA, o estudante deve descer a barra de rolagem da página até o final para localizar e acionar o botão 'Adicionar Turmas Selecionadas'. Já a turma T01 de MUSC12 (Composição Suplementar I) tem carga horária de 30 horas e está sob responsabilidade do docente Hermilo Pinheiro Santana."
    },
    "H2_19": {
        "Pergunta": "No curso de Letras Vernáculas com Língua Estrangeira Moderna do ILUFBA, qual é o processo formal para a escolha e o tempo de mandato do Coordenador e Vice-Coordenador do Colegiado, e qual é a nota mínima exigida em cada prova (escrita e oral) e o prazo máximo para entrega dos resultados pelas áreas acadêmicas à CAEL na avaliação de conhecimento prévio de línguas estrangeiras?",
        "Resposta Gabarito": "O Coordenador e o Vice-Coordenador são eleitos por escrutínio secreto em reunião específica dentre os membros docentes do Colegiado lotados no ILUFBA, para mandato de 2 anos (permitida 1 recondução). Já na avaliação de conhecimento prévio de línguas estrangeiras do ILUFBA, exige-se nota mínima igual ou superior a 5,0 (cinco) em cada uma das provas (escrita e oral, sendo a nota final expressa pela média aritmética de 0 a 10 com uma casa decimal), e as áreas acadêmicas têm o prazo de até 48 horas após a aplicação para entregar o resultado à Coordenação Acadêmica de Ensino de Letras (CAEL)."
    },
    "H2_20": {
        "Pergunta": "No Instituto de Letras da UFBA, quais eram os requisitos originais de aprovação prévia para submissão às avaliações de conhecimento prévio de nível intermediário e avançado em língua estrangeira, e qual é a competência do Colegiado em relação às decisões do(a) Coordenador(a)?",
        "Resposta Gabarito": "Originalmente, exigia-se aprovação prévia no nível básico para submeter-se à avaliação do nível intermediário e aprovação no nível intermediário para submeter-se ao nível avançado. Já em relação às decisões do(a) Coordenador(a), compete ao Colegiado deliberar sobre elas em grau de recurso."
    },
    "H2_21": {
        "Pergunta": "Em Línguas Estrangeiras no ILUFBA, qual passou a ser a periodicidade semestral e a distribuição nas duas primeiras semanas de aula dos exames de avaliação de conhecimento prévio (básico, intermediário e avançado), e qual é a atribuição do Colegiado no planejamento semestral da oferta de componentes?",
        "Resposta Gabarito": "Os exames de conhecimento prévio passaram a ser aplicados 1 vez por semestre letivo, nas 2 primeiras semanas de aula: as provas de nível básico e intermediário ocorrem na 1ª semana e a prova de nível avançado na 2ª semana, sendo cada nível pré-requisito para o seguinte. Quanto à oferta semestral, compete ao Colegiado planejar a oferta de componentes curriculares e definir seus horários para assegurar o cumprimento do turno do curso."
    },
    "H2_22": {
        "Pergunta": "Em Línguas Estrangeiras no ILUFBA, com que frequência semestral e em quais semanas eram originalmente aplicados os exames de conhecimento prévio antes da alteração de 2022, e qual é o quórum de instalação e o critério de votação das decisões do Colegiado?",
        "Resposta Gabarito": "Originalmente, os exames eram aplicados 2 vezes por semestre letivo: a partir da 2ª semana de aulas (básico na 2ª semana, intermediário na 3ª e avançado na 4ª) e na antepenúltima semana do semestre. Já o Colegiado instala-se com a presença da maioria absoluta de seus membros e delibera por maioria simples."
    },
    "H2_23": {
        "Pergunta": "Na Licenciatura em Matemática da UFBA, quais são os critérios de habilitação e o percentual mínimo de acerto para dispensa de disciplina anual por prova, e como se distribui a carga horária total de 3.158 horas do curso diurno para ingressantes a partir de 2007.1?",
        "Resposta Gabarito": "Habilitam-se à prova de dispensa de disciplina anual apenas discentes regularmente matriculados que tenham sido reprovados por média ou conceito no ano anterior, exigindo-se rendimento mínimo de 70% de acerto. No curso diurno (ingressantes a partir de 2007.1), as 3.158 horas distribuem-se em: Conteúdos Específicos (1.632h), Conteúdos Pedagógicos (306h), Dimensão Prática (408h), Estágio Docente (408h), Optativas (204h) e Atividades Complementares (200h)."
    },
    "H2_24": {
        "Pergunta": "Na Licenciatura em Matemática da UFBA, qual é a carga horária dedicada à Dimensão Prática e ao Estágio Docente no turno noturno, e quais são os limites máximos de horas aproveitáveis por participação em eventos científicos e culturais como Atividades Complementares no turno diurno?",
        "Resposta Gabarito": "Destinam-se 408 horas para a Dimensão Prática e 408 horas para o Estágio Docente. Já o aproveitamento máximo em eventos científicos e culturais como Atividades Complementares é de: 10 horas pela participação no evento, 20 horas por participação e autoria de trabalho apresentado, e 40 horas pela participação como membro da coordenação do evento."
    },
    "H2_25": {
        "Pergunta": "Na Faculdade de Medicina da Bahia (FMB), em qual prazo uma nova distribuição de internos realizada pelos Coordenadores de área deve ser referendada na Comissão de Internato, e quais são os nove Departamentos que compõem a estrutura básica da FMB?",
        "Resposta Gabarito": "A nova distribuição de internos feita pelos Coordenadores de área deve ser referendada na Comissão de Internato em até 60 dias. Os nove departamentos da FMB são: Anestesiologia e Cirurgia (DAC), Cirurgia Experimental e Especialidades Cirúrgicas (DCEEC), Ginecologia e Obstetrícia (DGO), Medicina Interna (DMED), Medicina Preventiva e Social (DMPS), Neurologia e Psiquiatria (DNPq), Patologia, Diagnóstico por Imagem e Medicina Legal (DPML), Pediatria (DPED) e Saúde da Família e Terapia Ocupacional (DSFTO)."
    },
    "H2_26": {
        "Pergunta": "Na Faculdade de Medicina da Bahia (FMB), qual é o prazo limite após o término do estágio para que professores e preceptores encaminhem as notas do Internato à Coordenação da Área, e qual é o tempo de mandato e a regra de recondução para Chefe e Vice-Chefe de Departamento?",
        "Resposta Gabarito": "No Internato, professores e preceptores devem encaminhar as notas à Coordenação da Área em até uma semana após o término do estágio. Já o mandato de Chefe e Vice-Chefe de Departamento na FMB é de dois anos, sendo permitida uma recondução em período consecutivo."
    },
    "H2_27": {
        "Pergunta": "Quais são as cinco modalidades e respectivas titulações dos cursos de graduação da UFBA e qual é o percentual máximo da carga horária total exigida para disciplinas optativas que um discente pode aproveitar?",
        "Resposta Gabarito": "As cinco modalidades são: I - Licenciatura (Licenciado); II - Bacharelado (Bacharel); III - Formação Profissional (diploma com a respectiva denominação); IV - Superior de Tecnologia (Tecnólogo); V - Bacharelado Interdisciplinar (Bacharel em Artes, Humanidades, Saúde ou C&T). O discente pode aproveitar até 70% (setenta por cento) da carga horária total exigida para disciplinas optativas."
    },
    "H2_28": {
        "Pergunta": "Na Escola de Música da UFBA, até que momento do calendário acadêmico é permitida a alteração das turmas selecionadas na matrícula on-line do SIGAA, e quantas vagas são reservadas para EMUS - Instrumento-MT na turma T03 de MUSD01 (Prática de Conjunto V)?",
        "Resposta Gabarito": "O estudante pode alterar as turmas selecionadas (adicionando ou removendo componentes) até a data final do período de matrícula on-line previsto no calendário acadêmico. Na turma T03 de MUSD01 (Prática de Conjunto V), há 8 vagas reservadas para EMUS - Instrumento-MT."
    },
    "H2_29": {
        "Pergunta": "No curso de Psicologia do IMS/UFBA, quais são os requisitos obrigatórios para que um docente exerça o cargo de Coordenador do Colegiado, e qual é a carga horária semanal máxima e a responsabilidade pela busca de locais no Estágio Supervisionado Não-Obrigatório?",
        "Resposta Gabarito": "O Coordenador deve ser docente do curso pertencente ao quadro permanente do IMS e possuir graduação em Psicologia. O Estágio Não-Obrigatório tem carga horária máxima de 30 horas semanais, cabendo integralmente ao discente angariar locais e propostas, sem qualquer responsabilidade de busca ou indicação por parte dos professores do estágio obrigatório."
    },
    "H2_30": {
        "Pergunta": "No curso de Terapia Ocupacional da UFBA, quais atitudes e expressões são estritamente proibidas aos estagiários no Estágio Obrigatório, e quais são as obrigações do campo concedente quanto a auxílio financeiro, seguro e crachá no Estágio Não-Obrigatório?",
        "Resposta Gabarito": "No Estágio Obrigatório, proíbem-se atitudes de desrespeito à diversidade e cultura e expressões de violência, racismo, capacitismo e outras formas de opressão. No Estágio Não-Obrigatório, o campo de estágio deve garantir auxílio financeiro ou bolsa, manter apólice de seguro para o estudante, respeitar a legislação vigente e confeccionar crachá no modelo orientado pelo CREFITO."
    },
    "H2_31": {
        "Pergunta": "Em Terapia Ocupacional na UFBA, a quem compete decidir sobre os casos omissos relativos ao Estágio Obrigatório, e qual é a exigência temporal para a formalização do Termo de Compromisso de Estágio (TCE) no Estágio Não-Obrigatório?",
        "Resposta Gabarito": "Os casos omissos do Estágio Obrigatório são resolvidos pelo Núcleo de Estágio e/ou órgãos superiores conforme sua competência. No Estágio Não-Obrigatório, é imprescindível que o Termo de Compromisso de Estágio (TCE) seja providenciado e formalizado antes do início das atividades, sob pena de infringir a Lei Federal nº 11.788/08."
    },
    "H2_32": {
        "Pergunta": "Na seleção para os cursos de graduação da UFBA, qual é o percentual de vagas reservado a egressos de escolas públicas e à faixa de renda igual ou inferior a 1,5 salário-mínimo per capita, e qual é o percentual máximo de aproveitamento da carga horária de disciplinas optativas (regra geral e regra para ingressantes anteriores a 2024.1)?",
        "Resposta Gabarito": "Reservam-se 50% das vagas a egressos de escolas públicas, destinando-se 50% destas aos estudantes com renda familiar per capita igual ou inferior a 1,5 salário-mínimo. Quanto às disciplinas optativas, o limite geral de aproveitamento é de 50% da carga horária total exigida, mantendo-se o teto de até 70% para ingressantes de semestres anteriores a 2024-1."
    },
    "H2_33": {
        "Pergunta": "No Instituto de Biologia da UFBA, quais docentes titulares e suplentes (e respectivas unidades externas) foram indicados em 2017 para a comissão de progressão funcional da professora Cláudia Luizon Dias Leme, e quais foram os três pontos de pauta sobre monitoria, PIBID/Bio e extensão apreciados pela Congregação em 2014?",
        "Resposta Gabarito": "Para a progressão da professora Cláudia Luizon Dias Leme foram indicadas como titulares Rejane Lira, Orane Falcão e Zênis Novaes (do IQui) e como suplentes Iara Bravo e Eudes Veloso (da FaFar). Já a pauta da Congregação em 2014 abordou: 1) Distribuição de Bolsas de Monitoria 2014.1 e 2014.2; 2) Indicação de novo coordenador do PIBID/Bio (gestão 2014-2018); 3) Aprovação de propostas e relatórios de ação de extensão."
    },
    "H2_34": {
        "Pergunta": "No Instituto de Biologia da UFBA, qual solução foi aprovada por unanimidade em 2017 para viabilizar a conclusão da disciplina BIO009 (Biologia Sanitária) diante da exoneração da professora Mércia, e qual foi o placar da votação e o motivo da abstenção da professora Alessandra Schnadelbach na análise de recursos de concurso em 2014?",
        "Resposta Gabarito": "Para a disciplina BIO009, aprovou-se por unanimidade colocar a coordenadora em contato com a professora substituta do 3º módulo (professora Dayane) para inverter os módulos e concluir o componente. Na análise dos recursos de concurso em 2014, houve deferimento por 8 votos a favor e 1 abstenção da professora Alessandra Schnadelbach (procuradora da candidata Maria Luiza Silveira de Carvalho), pois os candidatos atingiram a pontuação mínima de 300 pontos."
    },
    "H2_35": {
        "Pergunta": "Qual é a regra de representação docente na Congregação do Instituto de Geociências (IGEO) quando uma classe possui menos de 10% do total de professores, e como são classificados os componentes curriculares quanto à função e à natureza no Bacharelado em Matemática da UFBA?",
        "Resposta Gabarito": "Na Congregação do IGEO, cada classe docente tem um representante, mas quando uma classe possui menos de 10% do total de docentes, seus integrantes votam para a escolha da representação da classe imediatamente superior (ou da classe de associados, no caso de titulares). No Bacharelado em Matemática, os componentes classificam-se quanto à função em básico, profissional ou complementar, e quanto à natureza em obrigatória ou optativa."
    },
    "H2_36": {
        "Pergunta": "Qual é o prazo estabelecido no Instituto de Geociências (IGEO) para que os Colegiados e Núcleos Interdisciplinares encaminhem seus Regulamentos Internos à Congregação após a aprovação regimental pelo CONSUNI, e qual é o número total de vagas anuais (SISU e BI-CPL) do curso de Química Diurno da UFBA?",
        "Resposta Gabarito": "Os Colegiados de Graduação e Pós-Graduação e os Núcleos Interdisciplinares do IGEO têm o prazo de 180 dias, contados da aprovação regimental pelo Conselho Universitário, para encaminhar seus Regulamentos Internos à Congregação. Já o curso de Química Diurno oferta o total de 80 vagas anuais (64 via SISU e 16 via BI-CPL)."
    },
    "H2_37": {
        "Pergunta": "Qual é a penalidade aplicada no Instituto de Geociências (IGEO) aos membros docentes dos Colegiados que faltarem sem justificativa às reuniões, e o curso de Química da UFBA no turno noturno confere habilitação em Bacharelado?",
        "Resposta Gabarito": "No IGEO, perdem o mandato os docentes que faltarem sem justificativa a duas reuniões seguidas ou a quatro reuniões no mesmo exercício. Quanto ao curso de Química no turno noturno, ele não confere habilitação em Bacharelado, conferindo apenas o grau de Licenciatura."
    },
    "H2_38": {
        "Pergunta": "Como é calculada a proporção da representação estudantil nos órgãos colegiados do Instituto de Geociências (IGEO), e qual é o CEP correspondente ao endereço do Instituto de Física da UFBA?",
        "Resposta Gabarito": "Nos órgãos colegiados do IGEO, a representação discente é calculada na proporção de um estudante para cada quatro membros não discentes, desprezada a fração resultante. O endereço do Instituto de Física da UFBA possui o CEP 40.170-115."
    },
    "H2_39": {
        "Pergunta": "Quais são as quatro Seções que constituem a Coordenação Administrativa e Financeira (CAF) do Instituto de Geociências (IGEO), e quais foram os objetivos principais da reformulação curricular implementada em 1988 no Bacharelado em Matemática da UFBA?",
        "Resposta Gabarito": "A CAF do IGEO compõe-se de: a) Seção de Pessoal, Expediente e Transporte; b) Seção de Execução Financeira; c) Seção de Patrimônio, Arquivo e Almoxarifado; d) Seção de Manutenção, Limpeza e Vigilância. No Bacharelado em Matemática, a reforma de 1988 visou adequar o currículo à realidade discente, agrupar disciplinas em ciclo básico (até o 4º semestre) e profissionalizante (a partir do 5º), incluir disciplinas iniciais com base de nível médio sob abordagem superior e encadear pré-requisitos."
    },
    "H2_40": {
        "Pergunta": "Quais são as quatro seções que compõem a Coordenação Administrativa e Financeira (CAF) do Instituto de Geociências (IGEO), e quais são os direitos fundamentais garantidos ao discente orientando no desenvolvimento do TCC da Licenciatura em Computação?",
        "Resposta Gabarito": "No IGEO, a CAF divide-se em: Seção de Pessoal, Expediente e Transporte; Seção de Execução Financeira; Seção de Patrimônio, Arquivo e Almoxarifado; e Seção de Manutenção, Limpeza e Vigilância. Na Licenciatura em Computação, são direitos do orientando: ter professor-orientador e definir com ele a temática do TCC, receber orientação sobre o desenvolvimento e etapas do TCC e ser informado sobre as normas vigentes."
    },
    "H2_41": {
        "Pergunta": "Quais são os dois órgãos que constituem a Diretoria do Instituto de Geociências (IGEO), e quantas vagas anuais via SISU e via BI-CPL são ofertadas para os cursos de Física Diurno e Física Noturno da UFBA?",
        "Resposta Gabarito": "A Diretoria do IGEO é constituída pela Coordenação de Ensino e pela Coordenação Administrativa e Financeira. Para os cursos de Física da UFBA, o turno Diurno (Licenciatura/Bacharelado) oferta 40 vagas SISU e 10 vagas BI-CPL, enquanto o turno Noturno (Licenciatura) oferta 32 vagas SISU e 8 vagas BI-CPL."
    },
    "H2_42": {
        "Pergunta": "Quais são os quatro Departamentos que compõem o Instituto de Geociências (IGEO), e como se distribuem as 3.158 horas da Licenciatura em Matemática Diurno entre conteúdos científico-culturais, prática de ensino, estágio supervisionado e atividades complementares?",
        "Resposta Gabarito": "Os quatro Departamentos do IGEO são Geologia, Geografia, Geofísica e Oceanografia. Na Licenciatura em Matemática Diurno, as 3.158 horas dividem-se em: Conteúdos Científico-Culturais (1.938h), Prática de Ensino (Seminários Temáticos, Matemática para a Educação Básica I-III e Laboratório de Ensino I-II: 408h), Estágio Supervisionado (408h) e Atividades Complementares (200h)."
    },
    "H2_43": {
        "Pergunta": "Para quais órgãos superiores cabe recurso das decisões em primeira instância da Congregação do Instituto de Geociências (IGEO), e em qual cidade e estado está localizado o Instituto de Química da UFBA?",
        "Resposta Gabarito": "Das decisões em primeira instância da Congregação do IGEO cabe recurso para o Conselho Universitário (CONSUNI) ou para o Conselho Superior de Ensino, Pesquisa e Extensão (CONSEPE), segundo a matéria. O Instituto de Química da UFBA localiza-se em Salvador, Bahia."
    },
    "H2_44": {
        "Pergunta": "Qual é o e-mail oficial de contato do curso de Química da UFBA, e quais são os três perfis paradigmáticos de possíveis estudantes interessados no Bacharelado Interdisciplinar em Ciência e Tecnologia (BI-CT)?",
        "Resposta Gabarito": "O e-mail de contato para o curso de Química é grquim@ufba.br. Os três perfis de estudantes interessados no BI-CT são: a) alunos com perspectiva clara em C&T que visam Áreas de Concentração ou cursos de 2º ciclo; b) alunos da área que buscam formação flexível e generalista tendo a Grande Área como objetivo terminal; c) alunos que ainda não possuem escolha madura de especialização profissional, mas têm potencial para concluir curso na área de C&T."
    },
    "H2_45": {
        "Pergunta": "Qual é a oferta anual de vagas via BI-CPL para o curso de Física Noturno da UFBA, e qual é o limite máximo de horas que estudantes do Bacharelado em Matemática podem converter de programas institucionais de pesquisa, extensão ou monitoria em disciplinas optativas?",
        "Resposta Gabarito": "O curso de Física Noturno oferece 8 vagas anuais via BI-CPL. No Bacharelado em Matemática (Diurno), o estudante participante de programas institucionais de pesquisa, extensão ou monitoria pode converter seus trabalhos em carga horária curricular optativa até o limite máximo de 136 horas."
    },
    "H2_46": {
        "Pergunta": "Com que antecedência mínima em relação ao final das aulas o professor-orientador deve definir a composição da banca examinadora de TCC na Licenciatura em Computação, e quais são os endereços de e-mail de contato do Instituto de Física da UFBA?",
        "Resposta Gabarito": "Na Licenciatura em Computação, o professor-orientador deve definir a composição da banca examinadora até 15 (quinze) dias antes do final das aulas previstas no Calendário Acadêmico. Os e-mails de contato para os cursos do Instituto de Física são cgfis@ufba.br e ceag.fis@ufba.br."
    },
    "H2_47": {
        "Pergunta": "Quais são as duas alternativas exatas de titulação disponíveis no diploma para o egresso do Bacharelado Interdisciplinar em Humanidades conforme a escolha na segunda metade do curso, e qual é a antecedência mínima para formalizar a data de defesa do TCC no Bacharelado em Estudos de Gênero e Diversidade?",
        "Resposta Gabarito": "No BI em Humanidades, o egresso recebe o título de: 1) 'Bacharel em Humanidades' (se permanecer na Grande Área) ou 2) 'Bacharel em Humanidades com Área de Concentração em [título aprovado]' (se optar por área específica). No Bacharelado em Estudos de Gênero e Diversidade, a data de defesa do TCC deve ser formalizada na Secretaria do Colegiado e comunicada à comissão de monografia com antecedência mínima de 15 (quinze) dias."
    },
    "H2_48": {
        "Pergunta": "Qual componente curricular de Língua Portuguesa (e respectiva carga horária e objetivo) é exigido na Etapa de Formação Específica do Bacharelado Interdisciplinar em Humanidades, e qual é a atribuição da Coordenação Acadêmica do Instituto de Psicologia em relação à seleção de professores substitutos?",
        "Resposta Gabarito": "No BI em Humanidades, exige-se na Etapa de Formação Específica uma Optativa de Língua Portuguesa de 68 horas (como 'HAC – Oficina de Textos em Humanidades' ou equivalente) para trabalhar leitura e redação de textos acadêmicos na área. No Instituto de Psicologia, compete à Coordenação Acadêmica coordenar os processos seletivos para admissão de professores substitutos nas vagas da Unidade."
    },
    "H2_49": {
        "Pergunta": "Qual é a carga horária total e a duração mínima em semestres (e divisão entre etapas) do Bacharelado Interdisciplinar em Humanidades, e de quem depende exclusivamente a possibilidade de mudança no tema do TCC no curso de Estudos de Gênero e Diversidade?",
        "Resposta Gabarito": "O BI em Humanidades possui 2.400 horas totais e duração mínima de 6 semestres, divididos igualmente em Etapa de Formação Geral (1.200h) e Etapa de Formação Específica (1.200h). No curso de Estudos de Gênero e Diversidade, mudanças no tema do TCC dependem exclusivamente de acordo firmado entre docente orientador(a) e discente."
    },
    "H2_50": {
        "Pergunta": "Quais são os componentes curriculares obrigatórios e respectivas cargas horárias que integram o módulo 'Estudos sobre a Contemporaneidade' no Bacharelado Interdisciplinar em Humanidades, e o exercício da função de Coordenador de Núcleo Acadêmico no Instituto de Psicologia acarreta vantagem financeira?",
        "Resposta Gabarito": "No BI em Humanidades, o módulo 'Estudos sobre a Contemporaneidade' soma 136 horas, integrando dois componentes obrigatórios de 68 horas cada: HACA01 (Estudos sobre a Contemporaneidade I) e HACA34 (Estudos sobre a Contemporaneidade II). No Instituto de Psicologia, o cargo de Coordenador de Núcleo Acadêmico não constitui função gratificada, não gerando vantagem financeira."
    }
}

# ==============================================================================
# 50 PERGUNTAS HÍBRIDAS DE 3 PDFS (Q151 A Q200) — BRUTAS, SEM REFERÊNCIA A DOCS
# ==============================================================================
HIBRIDAS_3PDFS = {
    "H3_01": {
        "Pergunta": "No Instituto de Biologia da UFBA, em que data e sob organização de qual docente ocorreu o seminário 'Saberes e Ciências da Agroecologia' em 2017, quem foram os membros titulares aprovados para a banca de promoção de Adjunto IV para Associado I da professora Ana Verena Madeira, e por qual motivo a professora Rejane Lira declinou da coordenação do PIBID/Bio para o biênio 2014-2018?",
        "Resposta Gabarito": "O seminário 'Saberes e Ciências da Agroecologia' ocorreu em 17 de maio de 2017, organizado pela professora Maria Aparecida Oliveira. Os titulares aprovados para a banca de promoção da professora Ana Verena Madeira foram André Cruz, Francisco Barros e Rodrigo Johnson. Já a professora Rejane Lira declinou da coordenação do PIBID/Bio para não incidir em acúmulo vedado de bolsas, pois fora contemplada com bolsa de Produtividade em Pesquisa em Divulgação Científica do CNPq a partir de 01/03/2014."
    },
    "H3_02": {
        "Pergunta": "No Bacharelado em Ciência da Computação da UFBA, qual é a proporção percentual aproximada da carga horária mínima entre o eixo central obrigatório e os componentes optativos, qual é o limite máximo semanal de horas permitido para estágio discente (regra geral e exceção autorizada pelo Colegiado), e qual é a comprovação exigida e a carga horária semestral atribuída ao Estágio Supervisionado como atividade complementar de Vivência Profissional?",
        "Resposta Gabarito": "O eixo central obrigatório corresponde a cerca de 70% da carga horária mínima do curso e as optativas a cerca de 30%. O estágio discente limita-se a 20 horas semanais (4 horas diárias), podendo o Colegiado autorizar até 30 horas semanais após análise do desempenho acadêmico. Como atividade complementar de Vivência Profissional, o Estágio Supervisionado exige Termo de Compromisso e relatório de conclusão assinado pelos responsáveis, atribuindo-se 30 horas por semestre."
    },
    "H3_03": {
        "Pergunta": "Em Ciências Biológicas (Salvador) na UFBA, qual percentual mínimo da carga horária do curso é exigido como pré-requisito para inscrição em BIOA61 (Estágio Curricular Supervisionado do Bacharelado), qual é a ordem dos três critérios de prioridade definidos pelo Colegiado para distribuição de bolsas de monitoria, e por qual motivo a formação das bancas de progressão de Sheila Resende e Nei Nunes foi retirada de pauta em maio de 2017?",
        "Resposta Gabarito": "A inscrição em BIOA61 exige ter cumprido no mínimo 80% da carga horária do curso (condição de provável concluinte no semestre seguinte). A ordem de prioridade para bolsas de monitoria é: 1º projetos com maior número de alunos; 2º projetos que atendam turnos diurno e noturno; 3º projetos que contemplem aulas teóricas e práticas. As bancas de progressão de Sheila Resende e Nei Nunes foram retiradas de pauta por falta de entrega da solicitação e documentação."
    },
    "H3_04": {
        "Pergunta": "No Instituto de Biologia da UFBA, qual seria o caráter dos critérios de desempate para bolsas de monitoria caso a demanda superasse o número de bolsas concedidas em 2014, por que dois pontos de pauta referentes a bancas de promoção foram retirados de discussão em reunião extraordinária de 2017, e quais foram os quatro pontos sorteáveis aprovados para a seleção docente da matéria 'Ecologia e Metodologia de Pesquisa (Formulação de Problemas e Estatística)'?",
        "Resposta Gabarito": "Os critérios de desempate para bolsas de monitoria teriam caráter eliminatório segundo a gradação estabelecida pela comissão. Os dois pontos de pauta sobre bancas de promoção foram retirados porque os respectivos pareceres não foram encaminhados para a reunião. Os 4 pontos aprovados para 'Ecologia e Metodologia de Pesquisa' foram: 1) Ciência como resolução de problemas (do falseacionismo ao pluralismo metodológico); 2) Métodos de pesquisa nas ciências biológicas; 3) Papel da Ecologia frente à crise da biodiversidade; 4) O significado de p em estatística."
    },
    "H3_05": {
        "Pergunta": "No Instituto de Biologia da UFBA, por quantos dias a professora Ana Verena Madeira solicitou afastamento para missão científica em 2017 e qual único componente curricular manteve sob sua responsabilidade, quem foram os titulares indicados para a banca de promoção funcional da professora Ângela Maria Zanata (de Associado I para II), e qual foi o placar e a justificativa aceita pela Congregação para deferir os recursos de candidatas ao concurso docente de 2013?",
        "Resposta Gabarito": "A professora Ana Verena Madeira solicitou afastamento por 21 dias e manteve apenas o componente BIOA29 (Estágio em Docência II). Para a promoção da professora Ângela Maria Zanata foram indicados como titulares Blandina F. Viana, Iara Bravo e Marcelo Nápoli. Já os recursos ao concurso docente de 2013 foram deferidos por 8 votos a favor e 1 abstenção porque as candidatas atingiram a pontuação mínima exigida de 300 pontos na homologação das inscrições."
    },
    "H3_06": {
        "Pergunta": "Em Engenharia Elétrica na UFBA, qual foi o período de inscrição e quais docentes compuseram a chapa única eleita para a Coordenação do Colegiado (CCEE) em maio de 2021, qual é a carga horária total e o pré-requisito obrigatório da disciplina ENGC44 (Sistemas de Potência I), e quais são os prazos e condições para solicitação e avaliação plenária do Trabalho Final de Graduação (TFG) Intensivo?",
        "Resposta Gabarito": "A inscrição ocorreu de 10 a 12 de maio de 2021, elegendo-se a chapa única composta por André Pires Nóbrega Tahim (coordenador) e Maicon Deivid Pereira (vice-coordenador) para o biênio 2021-2023. A disciplina ENGC44 possui 68 horas teóricas no Departamento de Engenharia Elétrica e exige ENGC25 (Análise de Circuitos II) como pré-requisito. Já o TFG Intensivo deve ser solicitado até a data limite de entrega de propostas no semestre letivo anterior à realização e avaliado na última reunião plenária do CCEE daquele semestre anterior."
    },
    "H3_07": {
        "Pergunta": "Em Engenharia Química na UFBA, qual é o pré-requisito obrigatório de MAT 206 (Análise Real II), quais são as quatro disciplinas exigidas como pré-requisitos obrigatórios para ENG-D03 (Laboratório de Engenharia Química) e qual é a carga horária total e o módulo de ENG D05 (Mecânica dos Sólidos Aplicada a Plantas Industriais)?",
        "Resposta Gabarito": "Para MAT 206 (Análise Real II), o pré-requisito obrigatório é Análise Real I. Para ENG-D03 (Laboratório de Engenharia Química), os quatro pré-requisitos obrigatórios são ENG-353 (Cálculo de Reatores), ENG-358 (Fenômenos de Transporte II), ENG-426 (Operações Unitárias da Ind. Química I) e ENG-427 (Termodinâmica da Eng. Química II). Já o componente ENG D05 possui carga horária total de 68 horas e módulo de 40 horas."
    },
    "H3_08": {
        "Pergunta": "No curso de Engenharia de Agrimensura e Cartográfica da UFBA, qual foi a deliberação colegiada de fevereiro de 2025 sobre a unificação do Núcleo Docente Estruturante (NDE) com o Colegiado de Curso, qual é a carga horária total e a distribuição modular da disciplina ENG A57 (Administração Aplicada à Engenharia Civil), e quantos semestres foram estimados no planejamento de dilatação de prazo para que o aluno Francisco Cardoso dos Santos concluísse o curso?",
        "Resposta Gabarito": "Em fevereiro de 2025, o Colegiado (CCEAC) aprovou por unanimidade que o NDE do curso seja unificado ao próprio Colegiado de Curso. A disciplina ENG A57 possui carga horária total de 68 horas teóricas (T: 68, P: 00, E: 00) e distribuição modular de 40 horas. No processo de dilatação de prazo do aluno Francisco Cardoso dos Santos, estimou-se a necessidade de aproximadamente 8 semestres para finalizar o curso."
    },
    "H3_09": {
        "Pergunta": "Em Engenharia de Controle e Automação de Processos da UFBA, qual é o número de protocolo e em qual setor da PROGRAD tramitava o processo de reforma curricular isolada analisado pelo NDE em abril de 2022, qual é a equivalência no CCEQ da disciplina QUI-138 (Química Orgânica Fundamental III), e qual foi a decisão colegiada sobre o processo de trancamento de matrícula nº 23066.069320/2022-39 do estudante Rafael Ramos Santana Santos?",
        "Resposta Gabarito": "O processo de reforma curricular isolada possui o protocolo 23066.009857/2022-40 e encontrava-se no NUREC (Núcleo de Currículos/PROGRAD). A equivalência no CCEQ da disciplina QUI-138 é QUI-007. Já o processo de trancamento de matrícula nº 23066.069320/2022-39 do estudante Rafael Ramos Santana Santos foi julgado como Deferido por unanimidade pelo Colegiado."
    },
    "H3_10": {
        "Pergunta": "Em Engenharia de Controle e Automação de Processos da UFBA, quais departamentos foram consultados por ofício sobre a oferta de disciplinas para a reforma curricular e quais manifestaram concordância, qual é a equivalência oficial no CCEQ e os pré-requisitos obrigatórios de ENG-D06 (Engenharia Econômica e Gestão), e qual foi o posicionamento do Colegiado em outubro de 2016 acerca da proposta de retirada de pré-requisitos do CAE (e quais dois componentes integraram a discussão inicial de atualização)?",
        "Resposta Gabarito": "Foram consultados o Departamento de Ciência da Computação (DCC), o Departamento de Engenharia Elétrica (DEEC) e o Departamento de Química Geral e Inorgânica (DQGI), tendo o DEEC e o DQGI manifestado concordância. Para ENG-D06, a equivalência no CCEQ é ENG-362 e os pré-requisitos obrigatórios são ENG-426 (Operações Unitárias I) e MAT-D02 (Estatística na Engenharia). Em outubro de 2016, o Colegiado posicionou-se contra a retirada parcial ou total de pré-requisitos proposta pelo CAE e discutiu a atualização envolvendo ENG031 para ENGD07 e MATC29 para MATA48."
    },
    "H3_11": {
        "Pergunta": "Em Engenharia de Produção (Salvador) na UFBA, qual é o total de créditos e os pré-requisitos sugeridos para ENGF79 (Princípio dos Processos Contínuos), quais são os códigos dos pré-requisitos obrigatórios de ENGF80 (Sistemas de Produção Discreta), e qual é a carga horária total e a distribuição percentual das avaliações de ENG. 018 (Gestão e Planejamento Ambiental)?",
        "Resposta Gabarito": "A disciplina ENGF79 possui 3 créditos e sugere como pré-requisitos MATA03, FIS122 e FIS123. Para ENGF80, exigem-se como pré-requisitos obrigatórios ENG041 e ENG900. Já ENG. 018 possui 85 horas totais (51h teóricas e 34h práticas, 4 créditos) e distribui a avaliação em: Prova 1 (25%), Prova 2 (25%), Participação em aulas (10%) e Trabalho de Produção Limpa em empreendimentos (40%)."
    },
    "H3_12": {
        "Pergunta": "Na UFBA, qual é a carga horária mínima semanal de ensino e de aulas presenciais exigida dos docentes em regime de Dedicação Exclusiva (DE) ou Tempo Parcial (TP), em quais três situações específicas a universidade compartilha dados pessoais de estudantes de graduação para cumprimento de políticas públicas e obrigações legais, e quais são os requisitos mínimos de frequência e nota final para aprovação em um componente curricular?",
        "Resposta Gabarito": "Docentes em regime DE (40h) ou TP (20h) devem cumprir no mínimo 12 horas semanais de ensino, sendo pelo menos 10 horas de aulas presenciais. Os dados de graduandos são compartilhados com: 1) Inep (Censo Educacional), 2) MEC (Enade) e 3) empresa Integra (emissão da meia passagem Salvador Card, se solicitada). Para aprovação em componente curricular, exige-se frequência mínima de 75% e nota final igual ou superior a 5,0."
    },
    "H3_13": {
        "Pergunta": "Na UFBA, em quais três categorias o corpo docente dos cursos de pós-graduação stricto sensu deve ser credenciado pelo Colegiado, qual é o principal risco institucional em eventual incidente de segurança com dados pessoais (e por que a UFBA não está sujeita a multas pecuniárias da ANPD), e qual é a composição completa do Conselho Universitário (CONSUNI)?",
        "Resposta Gabarito": "Na pós-graduação stricto sensu, os docentes são credenciados nas categorias: I - Permanente, II - Colaborador e III - Visitante. Em incidentes de dados pessoais, o maior risco é afetar a reputação e imagem institucional, não havendo sanções pecuniárias da ANPD porque a UFBA é instituição pública federal. O CONSUNI compõe-se de: Reitor (Presidente), Vice-Reitor, pró-reitores administrativos, diretores das Unidades Universitárias, presidentes dos Conselhos Acadêmicos, 2 representantes docentes, 4 técnico-administrativos, 2 representantes da comunidade e representação discente."
    },
    "H3_14": {
        "Pergunta": "No curso de Tecnologia em Transporte Terrestre da UFBA, qual é a exigência de pré-requisito para cursar ENGJ64 (Legislação do Trânsito I), qual obra de Michael J. Bruton é recomendada para a disciplina ENG134 (Planejamento e Economia dos Transportes), e qual professor assina como Chefe do Departamento de Transportes a aprovação de ENGA62 (Logística dos Transportes)?",
        "Resposta Gabarito": "A disciplina ENGJ64 (Legislação do Trânsito I) não possui pré-requisitos ('Sem pré-requisito'). Para ENG134 (Planejamento e Economia dos Transportes), a obra recomendada de Michael J. Bruton é 'Introdução ao Planejamento dos Transportes' (Ed. Interciência, Rio de Janeiro, 1979). Já a aprovação de ENGA62 (Logística dos Transportes) é assinada pelo Prof. Artur Caldas Brandão, Chefe do DT-EPUFBA."
    },
    "H3_15": {
        "Pergunta": "Nos cursos de Ciências Sociais e Arqueologia da UFBA, quais são os limites percentuais máximos para o trancamento total e para o trancamento parcial de componentes curriculares, quantas vagas anuais via BI-CPL são oferecidas para o curso de História, e em qual semestre o estudante do Bacharelado Interdisciplinar em Humanidades deve fazer a opção pela Grande Área ou por uma Área de Concentração?",
        "Resposta Gabarito": "O trancamento total não pode ultrapassar 50% do tempo máximo de integralização e o trancamento parcial limita-se a 20% da carga horária total do curso. O curso de História oferece 10 vagas anuais via BI-CPL. No Bacharelado Interdisciplinar em Humanidades, a opção pela Grande Área ou por uma Área de Concentração deve ser feita na matrícula do 4º semestre."
    },
    "H3_16": {
        "Pergunta": "Como é definido o orientador de TCC no Bacharelado em Estudos de Gênero e Diversidade quando o discente não apresenta carta de aceite, em qual instância o Colegiado de Graduação do Instituto de Psicologia atua na proposta e aprovação de alterações curriculares, e qual é a carga horária total e semanal exigida para o 2º semestre do Bacharelado em Ciências Sociais da UFBA?",
        "Resposta Gabarito": "Em Estudos de Gênero e Diversidade, quando não há carta de aceite, a definição do orientador cabe à Comissão de TCC, validada em reunião de Colegiado. No Instituto de Psicologia, o Colegiado de Graduação propõe e aprova em primeira instância alterações curriculares do curso de Psicologia e das áreas de concentração no BI, além da criação e extinção de componentes. No Bacharelado em Ciências Sociais, o 2º semestre exige 390 horas totais e 26 horas semanais."
    },
    "H3_17": {
        "Pergunta": "Na UFBA, qual é a carga horária total e semanal exigida para o 4º semestre da Licenciatura em Ciências Sociais, qual é o pré-requisito obrigatório para cursar FCH290 (Pesquisa Histórica Supervisionada II) no Bacharelado em História, e como se distribui o quantitativo anual de vagas de ingresso entre os turnos diurno e noturno do curso de Pedagogia (Salvador)?",
        "Resposta Gabarito": "Na Licenciatura em Ciências Sociais, o 4º semestre possui 435 horas totais e 29 horas semanais. No Bacharelado em História, o pré-requisito obrigatório de FCH290 (Pesquisa Histórica Supervisionada II) é FCH289 (Pesquisa Histórica Supervisionada I). Em Pedagogia (Salvador), ofertam-se 90 vagas anuais no diurno (45 no 1º semestre e 45 no 2º) e 50 vagas anuais no noturno (no 2º semestre)."
    },
    "H3_18": {
        "Pergunta": "Em Ciências Sociais na UFBA, quais documentos e condições são exigidos para solicitar trancamento total de curso fora do prazo do calendário acadêmico, qual é a carga horária total e a carga horária destinada aos estágios obrigatórios na Licenciatura em Ciências Sociais, e em qual turno funciona o curso de Estudos de Gênero e Diversidade?",
        "Resposta Gabarito": "Para trancamento total fora do prazo, exige-se abertura de processo com requerimento e documentos comprobatórios da impossibilidade de cursar o semestre (como atestados médicos ou comprovantes de trabalho). A Licenciatura em Ciências Sociais possui 3.430 horas/aula totais, sendo 420 horas destinadas aos estágios curriculares obrigatórios (divididos em quatro componentes). O curso de Estudos de Gênero e Diversidade funciona no turno Noturno."
    },
    "H3_19": {
        "Pergunta": "Qual unidade universitária da UFBA é responsável por expedir o diploma do estudante do Bacharelado Interdisciplinar em Humanidades mesmo após a escolha de uma Área de Concentração, quais são os requisitos de formato e coautoria para o TCC em modalidade de produção científica em Estudos de Gênero e Diversidade, e a quais normas obedece a composição do Colegiado de Pós-Graduação do Instituto de Psicologia?",
        "Resposta Gabarito": "O estudante do BI em Humanidades permanece matriculado no IHAC, que expede seu diploma mesmo após a escolha de Área de Concentração. Em Estudos de Gênero e Diversidade, o TCC como produção científica deve ter formato de artigo ou ensaio, em coautoria entre discente e docente do curso. No Instituto de Psicologia, a composição do Colegiado de Pós-Graduação obedece às definições do regimento do respectivo Programa de Pós-Graduação e às normas gerais da UFBA."
    },
    "H3_20": {
        "Pergunta": "Na UFBA, qual é a carga horária mínima total de extensão exigida no Bacharelado em Ciências Sociais, quais são os quatro componentes curriculares que integram a lista de Optativas de Prática Pedagógica com código EDC0000 na Licenciatura em Ciências Sociais, e qual é o pré-requisito obrigatório para cursar FCH289 (Pesquisa Histórica Supervisionada I) no 7º semestre do Bacharelado em História?",
        "Resposta Gabarito": "No Bacharelado em Ciências Sociais, exigem-se no mínimo 265 horas de extensão. Na Licenciatura em Ciências Sociais, as quatro optativas com código EDC0000 são: Prática Pedagógica e Ações Colaborativas; Prática Pedagógica e Gestão; Prática Pedagógica e Dispositivos Materiais e Tecnológicos; e Prática Pedagógica, Docência e Atuação Profissional. No Bacharelado em História, o pré-requisito obrigatório de FCH289 é FCH435 (Técnicas de Elaboração de Projetos)."
    },
    "H3_21": {
        "Pergunta": "Na UFBA, qual é a carga horária total destinada aos componentes obrigatórios e às optativas com extensão em Design de Interiores, como se subdivide a carga horária total de 3.058 horas do curso de Biblioteconomia e Documentação, e a qual componente novo equivale o componente antigo 'COM112 - Oficina de Comunicação Audiovisual' na adaptação curricular de Jornalismo?",
        "Resposta Gabarito": "Em Design de Interiores, os componentes obrigatórios somam 1.800 horas (1.095h básico, 540h intermediário e 165h aprofundamento) e as optativas com extensão somam 405 horas. Em Biblioteconomia e Documentação, as 3.058 horas dividem-se em: Obrigatórios (2.448h / 80,05%), Optativos (306h / 10,01%), Estágio Supervisionado (204h / 6,67%) e Atividades Complementares (100h / 3,27%). Em Jornalismo, 'COM112 - Oficina de Comunicação Audiovisual' equivale a 'COMB81 – Jornalismo Integrado I'."
    },
    "H3_22": {
        "Pergunta": "Em Design de Interiores na UFBA, qual é o prazo e quais são as duas instâncias de avaliação para um pedido de reavaliação de nota de aprendizagem, como é calculada a nota final do trabalho monográfico (TCC) e a média mínima de aprovação em Biblioteconomia e Documentação, e em qual turno é oferecido o curso de Secretariado Executivo na Escola de Administração?",
        "Resposta Gabarito": "Em Design de Interiores, o pedido fundamentado de reavaliação deve ser encaminhado ao Departamento em até 3 dias úteis após a divulgação do resultado, sendo avaliado em 1ª instância pelo(s) professor(es) responsável(is) e em 2ª instância por comissão de três docentes designada pelo Departamento. Em Biblioteconomia, a nota final do TCC é a média aritmética das notas individuais da comissão examinadora, exigindo-se nota mínima de 5,0. O curso de Secretariado Executivo funciona no turno Diurno."
    },
    "H3_23": {
        "Pergunta": "Na UFBA, qual é a carga horária total exigida para integralização do Bacharelado em Design de Interiores, qual é o turno de funcionamento do curso de Engenharia de Produção, e em qual semestre letivo o estudante de Biblioteconomia e Documentação deve submeter os comprovantes das Atividades Complementares à comissão responsável (CPAC)?",
        "Resposta Gabarito": "A carga horária total de integralização de Design de Interiores é de 2.635 horas. O curso de Engenharia de Produção funciona no turno Diurno. Em Biblioteconomia e Documentação, os comprovantes de Atividades Complementares devem ser submetidos à CPAC no 8º (oitavo) semestre letivo do curso."
    },
    "H3_24": {
        "Pergunta": "Na UFBA, qual é o grau acadêmico oferecido pelo curso de Ciências Econômicas, em quais componentes curriculares o estudante de Biblioteconomia e Documentação deve estar matriculado no 8º semestre para ser considerado provável concluinte, e quais são as quatro modalidades aceitas (e a carga horária máxima por modalidade) nas Atividades Complementares do curso de Jornalismo?",
        "Resposta Gabarito": "Ciências Econômicas confere o grau de Bacharelado. Em Biblioteconomia e Documentação, é considerado provável concluinte no 8º semestre o estudante matriculado em ICIA37 (TCC II) e no Estágio Supervisionado em Biblioteconomia e Documentação. Em Jornalismo, as quatro modalidades de Atividades Complementares são Extensão, Pesquisa, Programas/Projetos/Representações Acadêmicos e Didática, com limite máximo de 180 horas por modalidade."
    },
    "H3_25": {
        "Pergunta": "Quais são os seis laboratórios e espaços de apoio acadêmico e de computação gráfica disponíveis na Escola de Belas Artes para dar suporte aos estudantes de Design de Interiores, e qual é o grau acadêmico conferido e o e-mail de contato do curso de Gestão do Turismo e Desenvolvimento Sustentável da UFBA?",
        "Resposta Gabarito": "Na Escola de Belas Artes, os seis espaços de apoio para Design de Interiores são: Laboratório de Poéticas Digitais (LPD), Núcleo de Computação Gráfica (LCG), LABDESIGN, EPICENTRO (co-working), FABLAB (Protótipos e Modelagem Digital) e Laboratório de Fotografia. Já o curso de Gestão do Turismo e Desenvolvimento Sustentável confere o grau de Tecnólogo e tem como e-mail de contato turismo@ufba.br."
    },
    "H3_26": {
        "Pergunta": "Na UFBA, qual é o turno de funcionamento do curso de Administração na Escola de Administração, quantas vagas anuais pelo SISU e pelo BI-CPL são ofertadas para o curso de Secretariado Executivo, e qual é o e-mail oficial de contato da Faculdade de Arquitetura para o curso de Arquitetura e Urbanismo?",
        "Resposta Gabarito": "O curso de Administração funciona no turno Diurno; o curso de Secretariado Executivo oferta anualmente 64 vagas pelo SISU e 16 vagas pelo BI-CPL; e o e-mail de contato da Faculdade de Arquitetura para o curso de Arquitetura e Urbanismo é arquitet@ufba.br."
    },
    "H3_27": {
        "Pergunta": "No curso de Biblioteconomia e Documentação da UFBA, quais são as cinco categorias de matrícula que garantem o ingresso no curso e quais são as durações mínima, média e máxima estabelecidas para sua conclusão, e quantas vagas anuais (SISU e BI-CPL) e qual endereço correspondem ao curso de Ciências Econômicas?",
        "Resposta Gabarito": "Em Biblioteconomia, as 5 categorias de matrícula são: I - classificado em processo seletivo; II - convênio nacional/estrangeiro, intercâmbio ou acordo cultural; III - aluno especial; IV - transferido ex-officio; V - transferido de cursos da UFBA ou outras IES. A duração de Biblioteconomia é de 4 anos (mínima), 5 anos (média) e 7 anos (máxima). Já Ciências Econômicas oferta 72 vagas SISU e 18 vagas BI-CPL, com endereço na Praça da Piedade, nº 6 - Piedade, Salvador, BA."
    },
    "H3_28": {
        "Pergunta": "No curso de Jornalismo da UFBA, a qual componente novo equivale o componente antigo 'COM126 - Oficina de Jornalismo Digital', como a disciplina Teoria da Percepção Visual (EBA 138) em Design define a percepção e sua importância no campo artístico, e quais são as atribuições conferidas ao Núcleo Docente Estruturante (NDE) no curso de Design de Interiores?",
        "Resposta Gabarito": "Em Jornalismo, 'COM126 - Oficina de Jornalismo Digital' equivale a 'COMB85 - Jornalismo Integrado V'. Em Design (EBA 138), a percepção é definida como processo cognitivo básico relevante nas áreas cognitivo-motora e afetivo-emocional e no repensar da formação artística, pessoal, social e profissional. Em Design de Interiores, compete ao NDE acompanhar, implementar, consolidar e atualizar continuamente o projeto pedagógico do curso, zelando pelo currículo, perfil do egresso e planos de ensino."
    },
    "H3_29": {
        "Pergunta": "Na UFBA, qual é o e-mail de contato da Faculdade de Ciências Contábeis, qual é o endereço completo e o CEP da Escola de Administração, e quantas vagas anuais via SISU são ofertadas para o curso de Secretariado Executivo?",
        "Resposta Gabarito": "O e-mail de contato da Faculdade de Ciências Contábeis é colegiadofcc@ufba.br; o endereço da Escola de Administração é Av. Reitor Miguel Calmon - Vale do Canela, Salvador, Bahia, CEP 40.110-903; e o curso de Secretariado Executivo oferta 64 vagas anuais via SISU."
    },
    "H3_30": {
        "Pergunta": "No curso de Gastronomia da UFBA, qual é o prazo para o aluno devolver o trabalho final de TCC II corrigido após sugestões de alterações pela Banca Examinadora, como funcionam o plantão de acolhimento e o atendimento individual do Serviço de Psicologia voltado aos discentes de Medicina do IMS, e qual é o critério de prioridade para oferta de componentes obrigatórios sem equivalência a alunos em adaptação curricular em Nutrição do IMS?",
        "Resposta Gabarito": "Em Gastronomia, o aluno tem o prazo de 7 dias para devolver o trabalho corrigido ao Coordenador do TCC II. No IMS, o Serviço de Psicologia oferta plantão de acolhimento psicológico imediato por ordem de chegada (sem agendamento) e psicoterapia individual mediante formulário no site do IMS/UFBA. Em Nutrição (IMS), a oferta de componentes obrigatórios sem equivalência na adaptação curricular é feita gradativamente, priorizando menor número de matrícula e maior coeficiente de rendimento."
    },
    "H3_31": {
        "Pergunta": "No curso de Gastronomia da UFBA, qual é o limite máximo de discentes e a carga horária semanal por turma de cada orientador no TCC II, qual é a composição numérica por segmento do Colegiado do Curso de Medicina do IMS/UFBA, e qual grupo de estudantes tem prioridade na escolha do local de estágio em Terapia Ocupacional (e a quem cabe decidir se não houver consenso)?",
        "Resposta Gabarito": "Em Gastronomia, o Coordenador do TCC II aloca no máximo 5 discentes por turma de cada orientador (com carga horária de 1 hora semanal), segundo disponibilidade docente e tema. O Colegiado de Medicina do IMS/UFBA é composto por 6 docentes, 2 representantes discentes e 1 técnico-administrativo. Em Terapia Ocupacional, têm prioridade na escolha do local de estágio os estudantes matriculados no Estágio II, cabendo a decisão ao Núcleo de Estágios caso não haja consenso."
    },
    "H3_32": {
        "Pergunta": "No curso de Gastronomia da UFBA, quem detém a competência para decidir os casos omissos referentes ao TCC, quais são os quatro tipos de evidências destacadas para a construção e avaliação de portfólios no curso de Medicina do IMS, e qual é o CEP da Escola de Medicina Veterinária e Zootecnia da UFBA?",
        "Resposta Gabarito": "Em Gastronomia, os casos omissos referentes ao TCC são decididos pelos respectivos Coordenadores dos componentes curriculares com anuência do Colegiado de Curso. Em Medicina (IMS), os 4 tipos de evidências para portfólios são: a) documentos produzidos nas atividades do curso; b) reproduções de fontes externas com fundamentações teóricas; c) avaliações por pares ou facilitador sobre o trabalho; d) produções que traduzem aprendizagens e reflexões. O CEP da Escola de Medicina Veterinária e Zootecnia é 40.170-115."
    },
    "H3_33": {
        "Pergunta": "O Trabalho de Conclusão de Curso (TCC) de Gastronomia da UFBA deve ser desenvolvido individualmente ou pode ser em dupla, qual é a média mínima exigida para aprovação em cada disciplina do Internato no curso de Medicina do IMS, e em qual Área do Conhecimento da UFBA está classificado o curso de Fisioterapia?",
        "Resposta Gabarito": "Em Gastronomia, o TCC deve ser desenvolvido estritamente de forma individual. Em Medicina (IMS), exige-se média mínima 5 (cinco) em cada disciplina para aprovação no Estágio Curricular Obrigatório (Internato). Já o curso de Fisioterapia está classificado na Área II: Ciências Biológicas e Saúde."
    },
    "H3_34": {
        "Pergunta": "Como se definem as responsabilidades do aluno e do professor orientador na elaboração do TCC de Gastronomia da UFBA, em qual rua e número fica o Instituto Multidisciplinar de Reabilitação e Saúde (sede de Fonoaudiologia), e a qual Área acadêmica da UFBA pertence o curso de Nutrição?",
        "Resposta Gabarito": "Em Gastronomia, a elaboração do TCC é de responsabilidade integral do aluno, o que não exime o professor orientador de desempenhar adequadamente suas atribuições de orientação. O Instituto Multidisciplinar de Reabilitação e Saúde situa-se na Rua Padre Feijó, nº 312. Já o curso de Nutrição pertence à Área II: Ciências Biológicas e Saúde."
    },
    "H3_35": {
        "Pergunta": "Qual é o tempo destinado à exposição oral do estudante e à arguição pela banca examinadora na apresentação do TCC II de Gastronomia da UFBA, qual é a oferta anual de vagas via BI-CPL e o e-mail de contato do curso de Ciências Econômicas, e qual é o procedimento de transição curricular exigido para estudantes não semestralizados até o 7º semestre no curso de Nutrição do IMS?",
        "Resposta Gabarito": "Na apresentação do TCC II de Gastronomia, o estudante dispõe de 20 minutos para exposição oral e a banca dispõe de até 20 minutos para arguição. O curso de Ciências Econômicas possui oferta anual de 18 vagas via BI-CPL e e-mail economia@ufba.br. Em Nutrição (IMS), estudantes não semestralizados no 7º semestre ou inferior devem ser incorporados ao currículo novo mediante assinatura de termo de concordância, obedecendo ao quadro de equivalência."
    },
    "H3_36": {
        "Pergunta": "Como se estrutura a avaliação do estágio supervisionado na atenção primária (modalidades e respectivos pesos) no curso de Enfermagem do IMS, quais são as matérias obrigatórias que compõem o Eixo das Ciências da Vida e Tecnológicas em Saúde Coletiva, e qual é o procedimento formal exigido para a substituição de orientador durante a elaboração do TCC em Gastronomia?",
        "Resposta Gabarito": "Em Enfermagem (IMS), a avaliação contínua do estágio na atenção primária utiliza três modalidades: avaliação do preceptor (peso 6), avaliação entre pares (dupla de estudantes) e avaliação do docente/supervisor com base em portfólio (peso 2). Em Saúde Coletiva (ISC), o Eixo das Ciências da Vida e Tecnológicas compreende: Estudo Morfo-Funcional Humano I e II, Estatística em Saúde e Informática em Saúde. Em Gastronomia, a substituição de orientador é permitida quando outro docente assume a orientação mediante formalização junto ao Coordenador do componente e ao Departamento."
    },
    "H3_37": {
        "Pergunta": "Compare os segmentos e quantitativos de representantes que compõem o Núcleo de Estágio do curso de Terapia Ocupacional, a Congregação da Faculdade de Medicina da Bahia (FMB) e o Colegiado do Curso de Medicina do IMS/UFBA.",
        "Resposta Gabarito": "Em Terapia Ocupacional, o Núcleo de Estágio reúne a vice-coordenação do curso, ao menos 1 docente terapeuta ocupacional, 1 técnico-administrativo (preferencialmente terapeuta ocupacional) e 1 discente. Na FMB, a Congregação compõe-se de Diretor, Vice-Diretor, representantes nos Conselhos Acadêmicos, Chefes de Departamento, Coordenadores de Colegiados (Graduação, Pós stricto sensu e COREME-HUPES/MCO), 3 representantes docentes, 2 técnico-administrativos e representantes discentes. No IMS/UFBA, o Colegiado de Medicina é integrado por 6 docentes, 2 representantes discentes e 1 técnico-administrativo."
    },
    "H3_38": {
        "Pergunta": "Na UFBA, qual é a oferta anual de vagas via BI-CPL para o curso de Zootecnia, quais são as regras de matrícula semestral e as cinco áreas de atuação abrangidas pelos estágios modulares no curso de Farmácia (Salvador), e sob qual condição temporal de mandato o Vice-Coordenador assume em definitivo a administração em caso de afastamento definitivo do Coordenador na Pós-Graduação em Ciência de Alimentos?",
        "Resposta Gabarito": "O curso de Zootecnia oferta 18 vagas anuais via BI-CPL. Em Farmácia (Salvador), a matrícula em estágio modular é única por semestre e abrange cinco áreas sob responsabilidade dos Departamentos: I - Farmácia Comunitária, II - Farmácia de Manipulação, III - Farmácia Hospitalar, IV - Análises de Alimentos e V - Análises Clínicas. Na Pós-Graduação em Ciência de Alimentos, em afastamento definitivo do Coordenador, o Vice-Coordenador assume apenas se já tiver sido cumprido 50% mais um dia do mandato; caso contrário, realiza-se nova eleição."
    },
    "H3_39": {
        "Pergunta": "Na UFBA, quais são os endereços de e-mail oficiais de contato dos colegiados dos cursos de graduação em Fisioterapia, Saúde Coletiva e Gastronomia?",
        "Resposta Gabarito": "Os e-mails oficiais de contato dos colegiados na UFBA são: fisioterapiaics@ufba.br para Fisioterapia; colegisc@ufba.br para Saúde Coletiva; e gatrocoleg@ufba.br para Gastronomia."
    },
    "H3_40": {
        "Pergunta": "Em qual endereço eletrônico deve ser consultada a oferta anual de vagas do curso de Educação do Campo - PARFOR da UFBA, quais são as regras de equivalência e limite de horas para Cursos de Certificação (realizados em IES e fora de IES) nas atividades complementares de Farmácia do IMS, e por quanto tempo são mantidos os componentes do currículo anterior sem equivalência na transição curricular de Nutrição do IMS?",
        "Resposta Gabarito": "A oferta de vagas de Educação do Campo - PARFOR deve ser consultada em ingresso.ufba.br/parfor-equidade. Em Farmácia (IMS), Cursos de Certificação realizados na UFBA ou em outras IES equivalem a 1h = 1h até o máximo de 60h/curso, e em instituições não-IES aproveitam de 1/2 a 1 das horas realizadas até o máximo de 30h/curso. Em Nutrição (IMS), componentes do currículo anterior sem equivalência ou com redução de carga horária são mantidos por 1 ano e meio (três semestres) a partir da implantação da nova matriz."
    },
    "H3_41": {
        "Pergunta": "Nos Bacharelados Interdisciplinares do IHAC/UFBA, qual é o meio obrigatório para a entrega dos documentos e certificados de Atividades Complementares, quais são os seis cargos mínimos obrigatórios que devem compor a Diretoria de uma Liga Acadêmica no ICTI (Campus Camaçari), e quais são os pré-requisitos obrigatórios exigidos para matrícula na disciplina ENG-426 (Operações Unitárias da Indústria Química I)?",
        "Resposta Gabarito": "Nos Bacharelados Interdisciplinares do IHAC, a entrega de cópias de documentos e certificados de Atividades Complementares deve ser feita exclusivamente por meio eletrônico, sendo vedada a entrega nas Coordenações. No ICTI, a Diretoria de cada Liga Acadêmica deve conter no mínimo: I - Diretoria Geral, II - Vice-diretoria, III - Secretaria Geral, IV - Coordenadoria Acadêmica, V - Coordenadoria Científica e VI - Coordenadoria de Extensão. Para ENG-426, os pré-requisitos obrigatórios são ENG-008 (Fenômenos de Transporte I) e ENG-396 (Termodinâmica I)."
    },
    "H3_42": {
        "Pergunta": "Na Escola de Música da UFBA, qual é a carga horária e a reserva de vagas para o curso EMUS - Música-MT na disciplina GMUS0042 (Metodologia da Educação Musical II), qual é o órgão responsável pelo julgamento em última instância de recursos contra decisões de Departamentos e Colegiados na Escola de Teatro, e qual é a porcentagem mínima de comparecimento às reuniões ordinárias exigida para emissão de certificado de participação no Colegiado de Letras Vernáculas?",
        "Resposta Gabarito": "Em Música, a disciplina GMUS0042 possui 90 horas e reserva 20 vagas para o curso EMUS - Música-MT. Na Escola de Teatro, cabe à Congregação julgar em último grau de recurso os processos contra decisões dos Departamentos e Colegiados. No Colegiado de Letras Vernáculas, exige-se o mínimo de 75% de comparecimento às reuniões ordinárias para emissão de certificado de participação."
    },
    "H3_43": {
        "Pergunta": "Na Escola de Música da UFBA, quantas vagas são reservadas para o curso EMUS - Música Popular-MT no componente GMUS0038 (ACCS: Etnomusicologia Negra), qual é o número mínimo de Professores Equivalentes da carreira do Magistério Superior exigido para compor um Departamento na Escola de Teatro, e qual é a regra sobre prioridade e obrigatoriedade de comparecimento dos membros às reuniões do Colegiado de Letras Vernáculas?",
        "Resposta Gabarito": "No componente GMUS0038 (ministrado por Pedro Fernando Acosta da Rosa), reservam-se 5 vagas para EMUS - Música Popular-MT. Na Escola de Teatro, um Departamento exige no mínimo 20 Professores(as) Equivalentes da carreira do Magistério Superior nele lotados. No Colegiado de Letras Vernáculas, o comparecimento às reuniões é obrigatório e tem prioridade sobre qualquer outra atividade universitária, respeitada a hierarquia entre órgãos colegiados."
    },
    "H3_44": {
        "Pergunta": "Na Escola de Música da UFBA, qual docente é responsável pela turma T01 de MUSA62 (Percepção Musical IV) e qual é a sua carga horária, qual é a duração do mandato e o limite de recondução para representantes docentes e técnico-administrativos na Congregação da Escola de Teatro, e quais são as atribuições do(a) Vice-Coordenador(a) no Colegiado de Letras Vernáculas?",
        "Resposta Gabarito": "Na Escola de Música, a turma T01 de MUSA62 (Percepção Musical IV) tem 30 horas e é ministrada por Ekaterina Konopleva. Na Congregação da Escola de Teatro, o mandato dos representantes docentes e técnico-administrativos é de 2 anos, permitida uma recondução. No Colegiado de Letras Vernáculas, compete ao(à) Vice-Coordenador(a): I - substituir o(a) Coordenador(a) quando necessário e II - colaborar e acompanhar as atividades da Coordenação."
    },
    "H3_45": {
        "Pergunta": "Na Escola de Música da UFBA, qual docente ministra a turma T02 da disciplina GMUS0004 (Estágio Supervisionado IV), qual é administrativamente o órgão de lotação dos servidores docentes e dos servidores técnico-administrativos na Escola de Teatro, e quantas faltas sem justificativa acarretam a perda de mandato dos membros no Colegiado de Letras Vernáculas?",
        "Resposta Gabarito": "Na Escola de Música, a turma T02 de GMUS0004 é ministrada pela docente Elisama da Silva Gonçalves Santos. Na Escola de Teatro, o órgão de lotação dos docentes é o Departamento e o dos técnico-administrativos é a Unidade Universitária. No Colegiado de Letras Vernáculas, perde o mandato o membro que faltar sem justificativa a 2 reuniões seguidas ou a 4 reuniões no mesmo exercício."
    },
    "H3_46": {
        "Pergunta": "Na Escola de Música da UFBA, qual é o docente responsável e a carga horária total do componente GMUS0038 (ACCS: Etnomusicologia Negra), qual é o órgão de lotação administrativa específico para docentes e técnico-administrativos na Escola de Teatro, e qual é o meio e a antecedência mínima exigidos para a convocação das reuniões ordinárias do Colegiado de Tradução e Línguas Clássicas?",
        "Resposta Gabarito": "Em Música, o componente GMUS0038 tem 60 horas de carga horária e é ministrado por Pedro Fernando Acosta da Rosa. Na Escola de Teatro, o órgão de lotação dos docentes é o Departamento e o dos técnico-administrativos é a Unidade Universitária. No Colegiado de Tradução e Línguas Clássicas, as reuniões ordinárias devem ser convocadas por ofício e/ou meio eletrônico com antecedência mínima de 48 horas, constando a respectiva ordem do dia."
    },
    "H3_47": {
        "Pergunta": "Na Escola de Música da UFBA, quantas turmas abertas existem para MUSA77 (História da Música I) e qual é o horário da turma T02, qual é o órgão de lotação administrativa de docentes e técnico-administrativos na Escola de Teatro, e quais são as cargas horárias semanais de atividade docente atribuídas à Coordenação, à Vice-Coordenação e aos Conselheiros no Colegiado de Letras Vernáculas?",
        "Resposta Gabarito": "Para MUSA77 (História da Música I), existem duas turmas abertas (T01 e T02), sendo o horário da T02 4M34 (19/08/2026 a 19/12/2026). Na Escola de Teatro, docentes são lotados no Departamento e técnico-administrativos na Unidade Universitária. No Colegiado de Letras Vernáculas, a carga horária semanal docente é de 20 horas para a Coordenação, 2 horas para a Vice-Coordenação e 1 hora para os Conselheiros."
    },
    "H3_48": {
        "Pergunta": "Na Escola de Música da UFBA, quantas vagas estão reservadas para o curso de Composição e Regência na turma T01 de MUSB11 (Composição II), quais são as três comissões específicas que integram obrigatoriamente o Núcleo de Ensino da Escola de Teatro, e quantos representantes docentes de áreas específicas e representantes técnico-administrativos compõem o Colegiado do Curso de Letras Vernáculas com uma Língua Estrangeira Moderna (CL402)?",
        "Resposta Gabarito": "Na turma T01 de MUSB11 (Composição II), reservam-se 6 vagas para Composição e Regência-Composição-MT. Na Escola de Teatro, integram o Núcleo de Ensino: o Núcleo Docente Estruturante (NDE), a Comissão de Estágio Supervisionado e a Comissão de Acompanhamento de TCC. Já o Colegiado do Curso de Letras Vernáculas com uma Língua Estrangeira Moderna (CL402) é composto por 14 representantes docentes de áreas específicas (Alemão, Espanhol, Francês, Inglês, Italiano, Latim, Libras, Português, Literaturas, Texto/Ensino/Discurso, PLE, Filologia, Teoria da Literatura e Faculdade de Educação), 1 representante técnico-administrativo e representação discente."
    },
    "H3_49": {
        "Pergunta": "Na Escola de Música da UFBA, qual é o docente responsável e a carga horária da disciplina MUSA02 (Arranjo para Música Popular I), como se realiza o processo de eleição do(a) Chefe e do(a) Vice-Chefe de Departamento na Escola de Teatro, e qual é o percentual mínimo de comparecimento às reuniões ordinárias exigido para emissão de certificado de participação aos membros do Colegiado de Tradução e Línguas Clássicas?",
        "Resposta Gabarito": "Na Escola de Música, MUSA02 possui 45 horas e tem como responsável o docente Ivan Bastos de Araujo Costa. Na Escola de Teatro, Chefe e Vice-Chefe de Departamento são eleitos em escrutínio secreto por maioria simples dos votos dos presentes à plenária departamental. No Colegiado de Tradução e Línguas Clássicas, exige-se comparecimento mínimo de 75% às reuniões ordinárias para emissão de certificado."
    },
    "H3_50": {
        "Pergunta": "Na Escola de Música da UFBA, qual é o horário de aula da turma T01 da disciplina MUSA04 (Arranjo para Música Popular III), quais atividades específicas da Escola de Teatro configuram-se como Curso de Extensão Permanente e como Projeto de Extensão Permanente, e qual é a duração do mandato e a regra de recondução para representantes docentes e técnico-administrativos no Colegiado de Letras Vernáculas?",
        "Resposta Gabarito": "Na Escola de Música, a turma T01 de MUSA04 funciona no horário 2T456. Na Escola de Teatro, o 'Curso Livre de Teatro' configura-se como Curso de Extensão Permanente e o 'Ato de 4' configura-se como Projeto de Extensão Permanente. No Colegiado de Letras Vernáculas, o mandato dos representantes docentes e técnico-administrativos é de 2 (dois) anos, permitida 1 (uma) recondução por igual período."
    }
}


def main():
    raw_path = "Experimento/backups/grupos_hibridas_brutos.json"
    with open(raw_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    rows = []
    q_counter = 1

    # 1. 100 Perguntas Únicas (1 PDF)
    for item in data["unicas"]:
        qid = f"Q{q_counter:03d}"
        q_counter += 1
        ov = UNICAS_OVERRIDES.get(qid, {})
        pergunta_clean = ov.get("Pergunta", item["Pergunta"])
        gabarito_clean = ov.get("Resposta Gabarito", item["Resposta Gabarito"])

        rows.append({
            "ID_Pergunta": qid,
            "Curso": item["Curso"],
            "Documento": item["Canonical_PDF"],
            "Classificação": "única",
            "Quantidade_PDFs": 1,
            "Grupo_Origem": "UNICA",
            "Pergunta": pergunta_clean,
            "Resposta Gabarito": gabarito_clean,
        })

    # 2. 50 Perguntas Híbridas de 2 PDFs
    for idx, pair in enumerate(data["pairs_2pdfs"]):
        gid = pair.get("id") or pair.get("group_id") or f"H2_{idx+1:02d}"
        items = pair.get("items") or pair
        synth = HIBRIDAS_2PDFS[gid]

        cursos_unicos = list(dict.fromkeys([it["Curso"] for it in items]))
        docs_unicos = list(dict.fromkeys([it["Canonical_PDF"] for it in items]))
        assert len(docs_unicos) == 2, f"Erro em {gid}: esperado 2 PDFs distintos, obteve {docs_unicos}"

        qid = f"Q{q_counter:03d}"
        q_counter += 1
        rows.append({
            "ID_Pergunta": qid,
            "Curso": "; ".join(cursos_unicos),
            "Documento": "; ".join(docs_unicos),
            "Classificação": "híbrida",
            "Quantidade_PDFs": 2,
            "Grupo_Origem": gid,
            "Pergunta": synth["Pergunta"],
            "Resposta Gabarito": synth["Resposta Gabarito"],
        })

    # 3. 50 Perguntas Híbridas de 3 PDFs
    for idx, triplet in enumerate(data["triplets_3pdfs"]):
        gid = triplet.get("id") or triplet.get("group_id") or f"H3_{idx+1:02d}"
        items = triplet.get("items") or triplet
        synth = HIBRIDAS_3PDFS[gid]

        cursos_unicos = list(dict.fromkeys([it["Curso"] for it in items]))
        docs_unicos = list(dict.fromkeys([it["Canonical_PDF"] for it in items]))
        assert len(docs_unicos) == 3, f"Erro em {gid}: esperado 3 PDFs distintos, obteve {docs_unicos}"

        qid = f"Q{q_counter:03d}"
        q_counter += 1
        rows.append({
            "ID_Pergunta": qid,
            "Curso": "; ".join(cursos_unicos),
            "Documento": "; ".join(docs_unicos),
            "Classificação": "híbrida",
            "Quantidade_PDFs": 3,
            "Grupo_Origem": gid,
            "Pergunta": synth["Pergunta"],
            "Resposta Gabarito": synth["Resposta Gabarito"],
        })

    df_out = pd.DataFrame(rows)
    assert len(df_out) == 200, f"Esperado 200 linhas, obteve {len(df_out)}"

    # Auditoria automática rigorosa para garantir que NENHUMA pergunta contenha referências a documentos
    forbidden_patterns = [
        r"\bart\.",
        r"\bartigo\b",
        r"\bresoluç",
        r"\bregimento\b",
        r"\bregulamento\b",
        r"\bppc\b",
        r"\bprojeto pedagógico\b",
        r"\bcatálogo\b",
        r"\bmanual\b",
        r"\bfluxograma\b",
        r"\bementa\b",
        r"\bementário\b",
        r"\banexo\b",
        r"\bpágina\b",
        r"\bpagina\b",
        r"\bdocumento\b",
        r"\bguia\b",
        r"\bata\b",
        r"\batas\b",
        r"\bregpg\b",
        r"\bestatuto\b",
        r"\binstrução normativa\b",
        r"\bin\s*01\b",
        r"\bnormas de\b",
        r"\brelatório\b",
        r"\bdiretrizes\b",
        r"§",
        r"\binciso\b",
        r"\bcaput\b",
        r"\bparágrafo\b",
    ]
    combined_rx = re.compile("|".join(forbidden_patterns), re.IGNORECASE)
    flagged = []
    for _, r in df_out.iterrows():
        m = combined_rx.search(str(r["Pergunta"]))
        if m:
            flagged.append((r["ID_Pergunta"], m.group(0), r["Pergunta"]))

    if flagged:
        print("ATENÇÃO - Perguntas com termos de referência detectados:")
        for qid, term, pq in flagged:
            print(f"  {qid} [{term}]: {pq}")
    else:
        print("AUDITORIA APROVADA: 0 referências a documentos/artigos/normas nas 200 perguntas!")

    out_200 = "Experimento/Conjunto de Testes 200.xlsx"
    df_out.to_excel(out_200, index=False)

    main_test_file = "Experimento/Conjunto de Testes.xlsx"
    df_out.to_excel(main_test_file, index=False)

    print(f"Sucesso! Atualizados '{out_200}' e '{main_test_file}' com {len(df_out)} perguntas brutas.")


if __name__ == "__main__":
    main()
