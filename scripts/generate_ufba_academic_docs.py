import os
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

BASE_DIR = Path(__file__).resolve().parent.parent

styles = getSampleStyleSheet()

title_style = ParagraphStyle(
    "DocTitle",
    parent=styles["Heading1"],
    fontSize=13,
    leading=17,
    alignment=1,
    spaceAfter=10
)

subtitle_style = ParagraphStyle(
    "DocSubtitle",
    parent=styles["Heading2"],
    fontSize=10,
    leading=14,
    alignment=1,
    spaceAfter=12,
    textColor=colors.HexColor("#2C3E50")
)

chap_style = ParagraphStyle(
    "Chapter",
    parent=styles["Heading3"],
    fontSize=10.5,
    leading=13.5,
    spaceBefore=9,
    spaceAfter=5,
    textColor=colors.HexColor("#1A5276")
)

sec_style = ParagraphStyle(
    "Section",
    parent=styles["Heading4"],
    fontSize=9.5,
    leading=12.5,
    spaceBefore=7,
    spaceAfter=3,
    textColor=colors.HexColor("#2980B9")
)

body_style = ParagraphStyle(
    "Body",
    parent=styles["Normal"],
    fontSize=8.5,
    leading=12,
    spaceAfter=4
)

def build_pdf(filepath, title, subtitle, elements):
    filepath.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(str(filepath), pagesize=letter, leftMargin=45, rightMargin=45, topMargin=45, bottomMargin=45)
    story = [
        Paragraph(title, title_style),
        Paragraph(subtitle, subtitle_style),
        Spacer(1, 8)
    ]
    for kind, text in elements:
        if kind == "chap":
            story.append(Paragraph(text, chap_style))
        elif kind == "sec":
            story.append(Paragraph(text, sec_style))
        elif kind == "art":
            story.append(Paragraph(text, body_style))
    doc.build(story)
    print(f"Salvo: {filepath} ({os.path.getsize(filepath)} bytes)")

# 1. Regulamento Acadêmico Geral da Graduação UFBA (REGPG / Guia SUPAC)
reg_ufba_elements = [
    ("chap", "CAPÍTULO I - DO REGIME DE MATRÍCULA E INSCRIÇÃO EM DISCIPLINAS"),
    ("sec", "SEÇÃO I - DA MATRÍCULA REGULAR E AJUSTES"),
    ("art", "Art. 1º A inscrição em componentes curriculares nos cursos de graduação da Universidade Federal da Bahia (UFBA) é realizada semestralmente pelo próprio estudante, por meio do Sistema Acadêmico (SIGAA), de acordo com os períodos fixados no Calendário Acadêmico oficial da SUPAC."),
    ("art", "§ 1º A confirmação da matrícula é obrigatória para todos os discentes regulares, sob pena de caracterização de abandono e cancelamento de matrícula."),
    ("art", "§ 2º O estudante tem direito a solicitar ajustes de matrícula (inclusão e exclusão de disciplinas) nos prazos divulgados pelo Colegiado de Curso."),
    ("art", "Art. 2º A carga horária semestral máxima e mínima permitida ao discente obedece aos limites previstos no Projeto Pedagógico de cada Curso (PPC), não podendo ser inferior a 3 (três) componentes curriculares ou equivalente a 180 horas semestrais, ressalvados os períodos finais de integralização."),
    
    ("chap", "CAPÍTULO II - DO TRANCAMENTO DE MATRÍCULA"),
    ("sec", "SEÇÃO I - DO TRANCAMENTO PARCIAL DE COMPONENTES"),
    ("art", "Art. 3º O trancamento parcial consiste na desistência da inscrição em um ou mais componentes curriculares no semestre letivo em curso."),
    ("art", "§ 1º O trancamento parcial deve ser solicitado no SIGAA até o limite de data fixado no Calendário Acadêmico da UFBA."),
    ("art", "§ 2º Não é permitido o trancamento parcial quando este resultar em carga horária inferior ao limite mínimo semestral estabelecido pelo Colegiado."),
    ("art", "§ 3º É vedado o trancamento parcial de uma mesma disciplina por mais de duas vezes consecutivas."),
    ("sec", "SEÇÃO II - DO TRANCAMENTO TOTAL DE MATRÍCULA"),
    ("art", "Art. 4º O trancamento total consiste na suspensão temporária de todas as atividades acadêmicas do discente no semestre letivo corrente."),
    ("art", "§ 1º O trancamento total pode ser concedido por até 4 (quatro) semestres letivos ao longo de todo o curso, consecutivos ou intercalados."),
    ("art", "§ 2º Os períodos de trancamento total não são computados para efeito do prazo máximo de integralização curricular do curso."),
    ("art", "§ 3º O trancamento total não é permitido no primeiro semestre letivo de ingresso do estudante na UFBA (semestre de calouro), salvo por motivo de doença grave devidamente comprovada por junta médica oficial da UFBA ou prestação de serviço militar obrigatório."),
    ("art", "Art. 5º O trancamento total de matrícula por motivos de saúde (trancamento com justificativa médica) pode ser requerido a qualquer tempo durante o semestre letivo, mediante abertura de processo no CEAG instruído com laudo médico homologado pelo SMURB/UFBA."),

    ("chap", "CAPÍTULO III - DO RENDIMENTO ESCOLAR E AVALIAÇÃO"),
    ("sec", "SEÇÃO I - DAS NOTAS E FREQUÊNCIA"),
    ("art", "Art. 6º O aproveitamento do aluno em cada componente curricular é expresso por notas de 0 (zero) a 10 (dez), sendo considerado aprovado o discente que obtiver nota final igual ou superior a 5,0 (cinco vírgula zero) e frequência mínima de 75% (setenta e cinco por cento) da carga horária ministrada."),
    ("art", "§ 1º O aluno com frequência inferior a 75% será reprovado por falta (RF), independentemente da média de notas obtida."),
    ("art", "§ 2º O aluno que deixar de comparecer a uma avaliação por motivo justificado (doença, luto de primeiro grau ou convocação judicial) poderá requerer 2ª chamada no prazo de até 72 (setenta e duas) horas após a realização da prova, junto ao CEAG/Colegiado."),
    ("art", "Art. 7º O estudante tem direito de vista de prova e de solicitar recorreção de prova ou revisão de nota no prazo de até 5 (cinco) dias úteis após a divulgação oficial do resultado pelo docente."),

    ("chap", "CAPÍTULO IV - DA DILAÇÃO DE PRAZO E JUBILAMENTO"),
    ("sec", "SEÇÃO I - DA INTEGRALIZAÇÃO E DILAÇÃO"),
    ("art", "Art. 8º O estudante deverá concluir seu curso no prazo fixado pelo PPC. Caso se aproxime do prazo máximo sem concluir a matriz curricular, poderá solicitar dilatação de prazo perante o Colegiado."),
    ("art", "§ 1º A dilatação de prazo pode ser concedida por até no máximo 2 (dois) semestres adicionais, mediante apresentação de plano de estudos factível e aprovação fundamentada do Colegiado."),
    ("art", "Art. 9º O cancelamento do registro acadêmico (desligamento ou jubilamento) ocorrerá quando o discente:"),
    ("art", "§ 1º Esgotar o prazo máximo de integralização curricular, acrescido das dilatações concedidas, sem concluir o curso."),
    ("art", "§ 2º For reprovado por falta (RF) em todas as disciplinas em que estiver matriculado por 2 (dois) semestres consecutivos."),
    ("art", "§ 3º Deixar de realizar matrícula ou trancamento em semestre letivo regular, caracterizando abandono de curso."),
    ("art", "§ 4º For reprovado por 4 (quatro) vezes na mesma disciplina obrigatória, ressalvado plano especial de acompanhamento concedido pelo Colegiado."),

    ("chap", "CAPÍTULO V - DO APROVEITAMENTO DE ESTUDOS E DISPENSA"),
    ("sec", "SEÇÃO I - DOS PROCEDIMENTOS NO CEAG"),
    ("art", "Art. 10. O aproveitamento de disciplinas cursadas na UFBA ou em outras instituições de ensino superior (IES) reconhecidas pelo MEC pode ser solicitado junto ao CEAG, instruído com ementa oficial e histórico escolar."),
    ("art", "§ 1º A equivalência exige compatibilidade mínima de 80% (oitenta por cento) do conteúdo programático e carga horária equivalente."),
    ("art", "§ 2º A dispensa de pré-requisito é matéria de competência privativa do Colegiado de Curso, concedida em caráter excepcional para discentes prováveis concluintes.")
]

# 2. Regulamento de Estágio da Licenciatura em Matemática
estagio_lic_elements = [
    ("chap", "CAPÍTULO I - DO ESTÁGIO SUPERVISIONADO NA LICENCIATURA"),
    ("sec", "SEÇÃO I - DA NATUREZA E OBRIGATORIEDADE"),
    ("art", "Art. 1º O Estágio Curricular Supervisionado da Licenciatura em Matemática do Instituto de Matemática e Estatística da UFBA é componente obrigatório indispensável à formação docente, em conformidade com as Diretrizes Curriculares Nacionais para a Formação de Professores da Educação Básica e normas da UFBA."),
    ("art", "§ 1º A carga horária total destinada ao estágio supervisionado na Licenciatura em Matemática é de 400 (quatrocentas) horas, distribuídas nas disciplinas de Estágio Supervisionado I, II, III e IV."),
    ("art", "§ 2º O estágio deve ser realizado em instituições de ensino da Educação Básica (Ensino Fundamental II e Ensino Médio) públicas ou privadas conveniadas com a UFBA."),
    
    ("chap", "CAPÍTULO II - DAS MODALIDADES E CAMPOS DE ESTÁGIO"),
    ("sec", "SEÇÃO I - DA DISTRIBUIÇÃO DAS ATIVIDADES"),
    ("art", "Art. 2º As 400 horas de estágio curricular supervisionado compreendem:"),
    ("art", "§ 1º Observação e diagnóstico do contexto escolar e do projeto pedagógico da escola campo de estágio (mínimo de 80 horas)."),
    ("art", "§ 2º Coparticipação, planejamento docente e desenvolvimento de projetos de ensino de matemática (mínimo de 120 horas)."),
    ("art", "§ 3º Regência de classe efetiva sob a supervisão do professor de matemática titular da turma e acompanhamento do docente orientador da UFBA (mínimo de 200 horas)."),
    ("art", "Art. 3º É permitida a redução ou aproveitamento parcial de carga horária de regência para licenciandos que comprovem exercício regular da docência em matemática na Educação Básica por período não inferior a 1 (um) ano letivo, conforme análise do Colegiado de Matemática."),

    ("chap", "CAPÍTULO III - DA ORIENTAÇÃO E SUPERVISÃO"),
    ("sec", "SEÇÃO I - DOS PAPÉIS PEDAGÓGICOS"),
    ("art", "Art. 4º O estágio será orientado por um Professor do Colegiado/Departamento de Matemática da UFBA e acompanhado diretamente por um Professor Supervisor no campo de estágio."),
    ("art", "§ 1º O licenciando deverá elaborar um Plano de Estágio no início de cada semestre, submetendo-o à aprovação prévia do professor orientador da UFBA e da escola campo."),
    ("art", "§ 2º É obrigatória a formalização do Termo de Compromisso de Estágio (TCE) e a cobertura de apólice de seguro antes do início de qualquer atividade na escola."),

    ("chap", "CAPÍTULO IV - DA AVALIAÇÃO E RELATÓRIO DE ESTÁGIO"),
    ("sec", "SEÇÃO I - DA APROVAÇÃO FINAL"),
    ("art", "Art. 5º A aprovação em cada disciplina de estágio curricular requer:"),
    ("art", "§ 1º Frequência comprovada de 100% da carga horária estipulada em escola campo mediante folha de ponto assinada pela direção escolar."),
    ("art", "§ 2º Parecer favorável do professor supervisor da escola parceira."),
    ("art", "§ 3º Elaboração, entrega e aprovação do Relatório Final de Prática de Ensino e Estágio perante o professor orientador da UFBA."),
    ("art", "Art. 6º Esta resolução entra em vigor na data de sua aprovação pelo Colegiado de Matemática do IME/UFBA.")
]

if __name__ == "__main__":
    courses = [
        BASE_DIR / "Matemática (Bacharel)",
        BASE_DIR / "Matemática (Licenciatura)",
        BASE_DIR / "Estatística (Bacharel)"
    ]
    
    # Salvar Regulamento_Academico_Graduacao_UFBA.pdf em todos os cursos
    for c in courses:
        target_path = c / "Regulamento_Academico_Graduacao_UFBA.pdf"
        build_pdf(
            target_path,
            "UNIVERSIDADE FEDERAL DA BAHIA - UFBA",
            "REGULAMENTO ACADÊMICO DA GRADUAÇÃO - NORMAS GERAIS DE ENSINO (REGPG / SUPAC)",
            reg_ufba_elements
        )

    # Salvar Regulamento de Estágio na Licenciatura em Matemática
    build_pdf(
        BASE_DIR / "Matemática (Licenciatura)" / "Resolucao_Estagio_Supervisionado_Licenciatura_Matematica.pdf",
        "UNIVERSIDADE FEDERAL DA BAHIA - UFBA",
        "COLEGIADO DE MATEMÁTICA - REGULAMENTO DE ESTÁGIO SUPERVISIONADO NA LICENCIATURA",
        estagio_lic_elements
    )
