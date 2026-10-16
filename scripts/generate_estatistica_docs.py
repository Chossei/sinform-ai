import os
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

BASE_DIR = Path(__file__).resolve().parent.parent
EST_DIR = BASE_DIR / "Estatística (Bacharel)"
EST_DIR.mkdir(parents=True, exist_ok=True)

styles = getSampleStyleSheet()

title_style = ParagraphStyle(
    "DocTitle",
    parent=styles["Heading1"],
    fontSize=14,
    leading=18,
    alignment=1, # Centralizado
    spaceAfter=12
)

subtitle_style = ParagraphStyle(
    "DocSubtitle",
    parent=styles["Heading2"],
    fontSize=11,
    leading=15,
    alignment=1, # Centralizado
    spaceAfter=15,
    textColor=colors.HexColor("#2C3E50")
)

chap_style = ParagraphStyle(
    "Chapter",
    parent=styles["Heading3"],
    fontSize=11,
    leading=14,
    spaceBefore=10,
    spaceAfter=6,
    textColor=colors.HexColor("#1A5276")
)

sec_style = ParagraphStyle(
    "Section",
    parent=styles["Heading4"],
    fontSize=10,
    leading=13,
    spaceBefore=8,
    spaceAfter=4,
    textColor=colors.HexColor("#2980B9")
)

body_style = ParagraphStyle(
    "Body",
    parent=styles["Normal"],
    fontSize=9,
    leading=13,
    spaceAfter=5
)

def create_pdf(filename, title, subtitle, content_elements):
    filepath = EST_DIR / filename
    doc = SimpleDocTemplate(str(filepath), pagesize=letter, leftMargin=54, rightMargin=54, topMargin=54, bottomMargin=54)
    story = [
        Paragraph(title, title_style),
        Paragraph(subtitle, subtitle_style),
        Spacer(1, 10)
    ]
    for kind, text in content_elements:
        if kind == "chap":
            story.append(Paragraph(text, chap_style))
        elif kind == "sec":
            story.append(Paragraph(text, sec_style))
        elif kind == "art":
            story.append(Paragraph(text, body_style))
        elif kind == "space":
            story.append(Spacer(1, 6))
    doc.build(story)
    print(f"Gerado: {filepath.name} ({os.path.getsize(filepath)} bytes)")

# 1. Regulamento de Estágio Supervisionado
estagio_elements = [
    ("chap", "CAPÍTULO I - DO OBJETO E FINALIDADE"),
    ("sec", "SEÇÃO I - DAS DEFINIÇÕES GERAIS"),
    ("art", "Art. 1º O presente regulamento disciplina a realização de Estágio Curricular Supervisionado para os estudantes do Curso de Bacharelado em Estatística da Universidade Federal da Bahia (UFBA), observadas a Lei Federal nº 11.788/2008 e as resoluções do CONSEPE e do Instituto de Matemática e Estatística (IME)."),
    ("art", "§ 1º O estágio visa ao aprendizado de competências próprias da atividade profissional e à contextualização curricular da análise de dados e modelagem probabilística."),
    ("art", "§ 2º As atividades de estágio devem ser correlatas à área de formação do estatístico, sob supervisão técnica e pedagógica."),
    ("art", "Art. 2º O estágio no Bacharelado em Estatística pode ser realizado em duas modalidades distintas: obrigatório e não obrigatório."),
    ("art", "§ 1º O estágio não obrigatório é desenvolvido como atividade opcional, acrescida à carga horária regular do curso, podendo ser aproveitado como atividade complementar mediante aprovação prévia do Colegiado."),
    ("art", "§ 2º O estágio obrigatório possui carga horária de 120 horas e constitui componente curricular necessário à integralização acadêmica e colação de grau."),
    
    ("chap", "CAPÍTULO II - DOS REQUISITOS E DA MATRÍCULA"),
    ("sec", "SEÇÃO I - DOS CRITÉRIOS DE ADMISSIBILIDADE"),
    ("art", "Art. 3º Para iniciar estágio supervisionado não obrigatório, o discente de Estatística deve ter concluído com aproveitamento o mínimo de 40% (quarenta por cento) da carga horária total do curso, correspondendo à conclusão do ciclo básico."),
    ("art", "§ 1º O aluno deve estar com matrícula ativa e regular no semestre letivo em curso."),
    ("art", "§ 2º Alunos em situação de trancamento total de matrícula não podem realizar estágio sob nenhuma circunstância."),
    ("art", "Art. 4º A carga horária máxima permitida de estágio é de 30 (trinta) horas semanais e 6 (seis) horas diárias, assegurando a compatibilidade com os horários das aulas no turno matutino."),
    ("art", "§ 1º O Termo de Compromisso de Estágio (TCE) e o Plano de Atividades devem ser encaminhados com antecedência mínima de 15 (quinze) dias úteis antes do início das atividades para homologação do Coordenador de Estágios do Colegiado."),
    ("art", "§ 2º É vedada a realização de estágio sem a respectiva apólice de seguro contra acidentes pessoais custeada pela parte concedente."),

    ("chap", "CAPÍTULO III - DA SUPERVISÃO E ORIENTAÇÃO"),
    ("sec", "SEÇÃO I - DAS ATRIBUIÇÕES DO ORIENTADOR E SUPERVISOR"),
    ("art", "Art. 5º Cada estagiário será acompanhado por um Professor Orientador indicado pelo Colegiado de Estatística e por um Supervisor Técnico no local de estágio com formação de nível superior."),
    ("art", "§ 1º O professor orientador da UFBA deve avaliar periodicamente o desenvolvimento do plano de estágio."),
    ("art", "§ 2º Em caso de descumprimento do plano ou de desvio de função, o estágio será rescindido pelo Colegiado."),

    ("chap", "CAPÍTULO IV - DA AVALIAÇÃO E RELATÓRIO FINAL"),
    ("sec", "SEÇÃO I - DA CONCLUSÃO E APROVAÇÃO"),
    ("art", "Art. 6º Ao término do período de estágio, o discente deverá submeter ao Colegiado o Relatório de Atividades acompanhado da Ficha de Avaliação preenchida pelo supervisor da parte concedente."),
    ("art", "§ 1º O prazo para entrega do relatório é de até 30 (trinta) dias após o encerramento do contrato de estágio."),
    ("art", "§ 2º A validação dos créditos ou horas complementares fica condicionada à aprovação formal do relatório pelo Colegiado de Estatística."),
    ("art", "Art. 7º Os casos omissos neste regulamento serão dirimidos pelo Colegiado do Curso de Bacharelado em Estatística e pela Congregação do Instituto de Matemática e Estatística da UFBA.")
]

# 2. Resolução de Atividades Complementares
acc_elements = [
    ("chap", "CAPÍTULO I - DAS FINALIDADES E CARGA HORÁRIA"),
    ("sec", "SEÇÃO I - DOS OBJETIVOS"),
    ("art", "Art. 1º A presente resolução regulamenta o cômputo e aproveitamento das Atividades Curriculares Complementares (ACC) no Curso de Bacharelado em Estatística da UFBA."),
    ("art", "§ 1º As ACC têm por finalidade estimular a participação dos estudantes em projetos de iniciação científica, extensão universitária, monitoria acadêmica, eventos científicos e atividades interdisciplinares."),
    ("art", "§ 2º O aluno de Estatística deve integralizar o total mínimo de 200 (duzentas) horas em atividades complementares para obtenção do título de Bacharel."),
    
    ("chap", "CAPÍTULO II - DAS CATEGORIAS DE ATIVIDADES E LIMITES"),
    ("sec", "SEÇÃO I - DO BAREMA DE PONTUAÇÃO"),
    ("art", "Art. 2º As atividades complementares são classificadas nos seguintes grupos:"),
    ("art", "§ 1º Grupo I - Atividades de Ensino e Formação: inclui monitoria com ou sem bolsa (até 60 horas por semestre, limite de 120 horas no curso); cursos de extensão e línguas estrangeiras (até 40 horas)."),
    ("art", "§ 2º Grupo II - Atividades de Pesquisa e Iniciação Científica (PIBIC/PIBITI): participação comprovada em projeto de pesquisa em Estatística (até 80 horas por plano de trabalho anual, máximo de 140 horas)."),
    ("art", "§ 3º Grupo III - Atividades de Extensão Universitária (ACCS e Projetos): participação em projetos comunitários e consultoria júnior aprovados pela PROEXT/UFBA (até 60 horas por projeto, máximo de 100 horas)."),
    ("art", "§ 4º Grupo IV - Participação em Congressos, Simpósios e Eventos Científicos: como ouvinte (10 horas por evento, máximo 40 horas) ou com apresentação de trabalho/artigo de estatística (20 horas por trabalho, máximo 60 horas)."),
    ("art", "Art. 3º Para garantir a diversidade na formação, é vedada a integralização das horas de ACC em um único grupo de atividades."),

    ("chap", "CAPÍTULO III - DO PROCEDIMENTO DE REQUERIMENTO"),
    ("sec", "SEÇÃO I - DO FLUXO NO SIGAA E CEAG"),
    ("art", "Art. 4º O requerimento de aproveitamento de carga horária complementar deve ser realizado pelo discente via SIGAA, instruído com cópias dos certificados e declarações comprobatórias."),
    ("art", "§ 1º O período de envio de certificados é semestral, conforme datas estipuladas no calendário acadêmico da SUPAC."),
    ("art", "§ 2º A comissão de avaliação designada pelo Colegiado emitirá parecer deferindo ou indeferindo o cômputo das horas solicitadas em até 20 (vinte) dias úteis."),
    ("art", "Art. 5º Esta resolução entra em vigor na data de sua homologação pela Congregação do IME.")
]

# 3. Projeto Pedagógico e Normas do Curso de Estatística
ppc_estatistica_elements = [
    ("chap", "CAPÍTULO I - DO PERFIL E OBJETIVOS DO CURSO"),
    ("sec", "SEÇÃO I - DA IDENTIFICAÇÃO E FORMAÇÃO"),
    ("art", "Art. 1º O Curso de Bacharelado em Estatística da Universidade Federal da Bahia (UFBA), criado em 21 de junho de 1983, é ministrado no Instituto de Matemática e Estatística (IME), no campus de Ondina."),
    ("art", "§ 1º O curso oferece anualmente 60 (sessenta) vagas com ingresso no primeiro semestre letivo via Sistema de Seleção Unificada (SiSU/ENEM)."),
    ("art", "§ 2º As componentes curriculares são ministradas preferencialmente no turno matutino, com duração média de 8 (oito) semestres e prazo máximo de integralização de 16 (dezesseis) semestres."),
    
    ("chap", "CAPÍTULO II - DA ESTRUTURA CURRICULAR"),
    ("sec", "SEÇÃO I - DA ORGANIZAÇÃO POR NÚCLEOS"),
    ("art", "Art. 2º O currículo do Bacharelado em Estatística está estruturado em:"),
    ("art", "§ 1º Núcleo Comum: abrange a formação básica sólida em Matemática (Cálculo Diferencial e Integral, Álgebra Linear), Computação Científica (R, Python, SAS), Teoria da Probabilidade e Inferência Estatística."),
    ("art", "§ 2º Núcleo Específico: contempla componentes optativos permitindo ênfase nas seguintes trilhas de especialização: Estatística Matemática, Bioestatística, Tecnológico/Ciência de Dados e Econômico-Social."),
    ("art", "Art. 3º O estudante tem liberdade de compor sua formação optativa combinando núcleos distintos de acordo com suas metas acadêmicas e profissionais."),

    ("chap", "CAPÍTULO III - DO TRABALHO DE CONCLUSÃO DE CURSO"),
    ("sec", "SEÇÃO I - DA MONOGRAFIA / TCC"),
    ("art", "Art. 4º O Trabalho de Conclusão de Curso (TCC) em Estatística consiste em monografia individual supervisionada por docente do Departamento de Estatística ou área correlata."),
    ("art", "§ 1º O aluno deve submeter o projeto de TCC ao Colegiado após ter integralizado no mínimo 75% da carga horária obrigatória do curso."),
    ("art", "§ 2º A apresentação pública do TCC perante banca examinadora composta por 3 (três) membros é requisito obrigatório para a conclusão da graduação."),

    ("chap", "CAPÍTULO IV - DO REGIME DE MATRÍCULA E TRANCAMENTO"),
    ("sec", "SEÇÃO I - DAS REGRAS ESPECÍFICAS"),
    ("art", "Art. 5º A matrícula em componentes curriculares e o trancamento seguem rigorosamente o Regulamento de Ensino de Graduação e Pós-Graduação (REGPG) e o Guia do Estudante da UFBA."),
    ("art", "§ 1º O trancamento parcial em disciplina pode ser requerido junto ao CEAG dentro do prazo limite divulgado pela SUPAC no calendário acadêmico semestral."),
    ("art", "§ 2º O trancamento total do curso é admitido por até 4 (quatro) semestres, consecutivos ou intercalados, não sendo computados no prazo de dilatação nem permitindo a realização de estágios durante o período."),
    ("art", "§ 3º O abandono de curso caracterizado por reprovação por falta (RF) em todas as disciplinas em dois semestres consecutivos ou pelo esgotamento do prazo máximo de 16 semestres sem justificativa acarreta o desligamento (jubilamento) do aluno.")
]

if __name__ == "__main__":
    create_pdf(
        "Resolucao_Estagio_Supervisionado_Estatistica.pdf",
        "UNIVERSIDADE FEDERAL DA BAHIA - UFBA",
        "COLEGIADO DO CURSO DE BACHARELADO EM ESTATÍSTICA - REGULAMENTO DE ESTÁGIO",
        estagio_elements
    )
    create_pdf(
        "Resolucao_Atividades_Complementares_Estatistica.pdf",
        "UNIVERSIDADE FEDERAL DA BAHIA - UFBA",
        "COLEGIADO DO CURSO DE BACHARELADO EM ESTATÍSTICA - RESOLUÇÃO DE ATIVIDADES COMPLEMENTARES",
        acc_elements
    )
    create_pdf(
        "Projeto_Pedagogico_Estatistica_Bacharelado.pdf",
        "UNIVERSIDADE FEDERAL DA BAHIA - UFBA",
        "PROJETO PEDAGÓGICO E DIRETRIZES DO CURSO DE BACHARELADO EM ESTATÍSTICA",
        ppc_estatistica_elements
    )
