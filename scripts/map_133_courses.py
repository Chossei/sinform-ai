"""
Mapeamento dos 133 cursos de graduação da Universidade Federal da Bahia (UFBA)
Organizados nas 8 Grandes Áreas do Conhecimento (CNPq) + UFBA - Geral.
"""

COURSES_DATA = [
    # =========================================================================
    # 1. CIÊNCIAS EXATAS E DA TERRA (18 cursos)
    # =========================================================================
    {
        "nome": "Ciência da Computação",
        "grau": "Bacharel",
        "area": "Ciências Exatas e da Terra",
        "campus": "Salvador (Ondina)",
        "unidade": "Instituto de Computação (IC)",
        "email": "ccc@ufba.br",
        "site": "https://computacao.ufba.br",
        "sigaa_id": "1876874"
    },
    {
        "nome": "Computação",
        "grau": "Licenciatura",
        "area": "Ciências Exatas e da Terra",
        "campus": "Salvador (Ondina)",
        "unidade": "Instituto de Computação (IC)",
        "email": "lc@ufba.br",
        "site": "https://computacao.ufba.br",
        "sigaa_id": "1876873"
    },
    {
        "nome": "Sistemas de Informação",
        "grau": "Bacharel",
        "area": "Ciências Exatas e da Terra",
        "campus": "Salvador (Ondina)",
        "unidade": "Instituto de Computação (IC)",
        "email": "bsi@ufba.br",
        "site": "https://computacao.ufba.br",
        "sigaa_id": "1876875"
    },
    {
        "nome": "Estatística",
        "grau": "Bacharel",
        "area": "Ciências Exatas e da Terra",
        "campus": "Salvador (Ondina)",
        "unidade": "Instituto de Matemática e Estatística (IME)",
        "email": "colest@ufba.br",
        "site": "https://colest.ime.ufba.br",
        "sigaa_id": "1876870"
    },
    {
        "nome": "Matemática",
        "grau": "Bacharel",
        "area": "Ciências Exatas e da Terra",
        "campus": "Salvador (Ondina)",
        "unidade": "Instituto de Matemática e Estatística (IME)",
        "email": "colmat@ufba.br",
        "site": "https://colmat.ufba.br",
        "sigaa_id": "1876871"
    },
    {
        "nome": "Matemática",
        "grau": "Licenciatura",
        "area": "Ciências Exatas e da Terra",
        "campus": "Salvador (Ondina)",
        "unidade": "Instituto de Matemática e Estatística (IME)",
        "email": "colmat@ufba.br",
        "site": "https://colmat.ufba.br",
        "sigaa_id": "1876848"
    },
    {
        "nome": "Física",
        "grau": "Bacharel",
        "area": "Ciências Exatas e da Terra",
        "campus": "Salvador (Ondina)",
        "unidade": "Instituto de Física (IF)",
        "email": "cgfis@ufba.br",
        "site": "https://fisica.ufba.br",
        "sigaa_id": "1876865"
    },
    {
        "nome": "Física",
        "grau": "Licenciatura",
        "area": "Ciências Exatas e da Terra",
        "campus": "Salvador (Ondina)",
        "unidade": "Instituto de Física (IF)",
        "email": "cgfis@ufba.br",
        "site": "https://fisica.ufba.br",
        "sigaa_id": "1876866"
    },
    {
        "nome": "Geofísica",
        "grau": "Bacharel",
        "area": "Ciências Exatas e da Terra",
        "campus": "Salvador (Barra/Ondina)",
        "unidade": "Instituto de Geociências (IGEO)",
        "email": "colgeof@ufba.br",
        "site": "https://igeo.ufba.br",
        "sigaa_id": "1876856"
    },
    {
        "nome": "Geologia",
        "grau": "Bacharel",
        "area": "Ciências Exatas e da Terra",
        "campus": "Salvador (Barra/Ondina)",
        "unidade": "Instituto de Geociências (IGEO)",
        "email": "geologia@ufba.br",
        "site": "https://igeo.ufba.br",
        "sigaa_id": "1876857"
    },
    {
        "nome": "Oceanografia",
        "grau": "Bacharel",
        "area": "Ciências Exatas e da Terra",
        "campus": "Salvador (Barra/Ondina)",
        "unidade": "Instituto de Geociências (IGEO)",
        "email": "oceanografia@ufba.br",
        "site": "https://igeo.ufba.br",
        "sigaa_id": "1876858"
    },
    {
        "nome": "Geografia",
        "grau": "Bacharel",
        "area": "Ciências Exatas e da Terra",
        "campus": "Salvador (Barra/Ondina)",
        "unidade": "Instituto de Geociências (IGEO)",
        "email": "colgeo@ufba.br",
        "site": "https://igeo.ufba.br",
        "sigaa_id": "1876859"
    },
    {
        "nome": "Geografia",
        "grau": "Licenciatura",
        "area": "Ciências Exatas e da Terra",
        "campus": "Salvador (Barra/Ondina)",
        "unidade": "Instituto de Geociências (IGEO)",
        "email": "colgeo@ufba.br",
        "site": "https://igeo.ufba.br",
        "sigaa_id": "1876860"
    },
    {
        "nome": "Química",
        "grau": "Bacharel",
        "area": "Ciências Exatas e da Terra",
        "campus": "Salvador (Ondina)",
        "unidade": "Instituto de Química (IQ)",
        "email": "colqui@ufba.br",
        "site": "https://quimica.ufba.br",
        "sigaa_id": "1876850"
    },
    {
        "nome": "Química",
        "grau": "Licenciatura",
        "area": "Ciências Exatas e da Terra",
        "campus": "Salvador (Ondina)",
        "unidade": "Instituto de Química (IQ)",
        "email": "colqui@ufba.br",
        "site": "https://quimica.ufba.br",
        "sigaa_id": "1876851"
    },
    {
        "nome": "Química Industrial",
        "grau": "Bacharel",
        "area": "Ciências Exatas e da Terra",
        "campus": "Salvador (Ondina)",
        "unidade": "Instituto de Química (IQ)",
        "email": "colqui@ufba.br",
        "site": "https://quimica.ufba.br",
        "sigaa_id": "1876852"
    },
    {
        "nome": "BI em Ciência e Tecnologia",
        "grau": "Bacharel",
        "area": "Ciências Exatas e da Terra",
        "campus": "Salvador (Ondina)",
        "unidade": "Instituto de Humanidades, Artes e Ciências (IHAC)",
        "email": "ihac@ufba.br",
        "site": "https://ihac.ufba.br",
        "sigaa_id": "1876930"
    },

    # =========================================================================
    # 2. ENGENHARIAS (16 cursos)
    # =========================================================================
    {
        "nome": "Engenharia Civil",
        "grau": "Bacharel",
        "area": "Engenharias",
        "campus": "Salvador (Federação)",
        "unidade": "Escola Politécnica (POLI)",
        "email": "civil@ufba.br",
        "site": "https://eng.ufba.br",
        "sigaa_id": "1876910"
    },
    {
        "nome": "Engenharia da Computação",
        "grau": "Bacharel",
        "area": "Engenharias",
        "campus": "Salvador (Federação)",
        "unidade": "Escola Politécnica (POLI)",
        "email": "engcomputacao@ufba.br",
        "site": "https://eng.ufba.br",
        "sigaa_id": "1876911"
    },
    {
        "nome": "Engenharia de Agrimensura e Cartográfica",
        "grau": "Bacharel",
        "area": "Engenharias",
        "campus": "Salvador (Federação)",
        "unidade": "Escola Politécnica (POLI)",
        "email": "agrimensura@ufba.br",
        "site": "https://eng.ufba.br",
        "sigaa_id": "1876912"
    },
    {
        "nome": "Engenharia de Controle e Automação de Processos",
        "grau": "Bacharel",
        "area": "Engenharias",
        "campus": "Salvador (Federação)",
        "unidade": "Escola Politécnica (POLI)",
        "email": "engautomacao@ufba.br",
        "site": "https://eng.ufba.br",
        "sigaa_id": "1876913"
    },
    {
        "nome": "Engenharia de Minas",
        "grau": "Bacharel",
        "area": "Engenharias",
        "campus": "Salvador (Federação)",
        "unidade": "Escola Politécnica (POLI)",
        "email": "minas@ufba.br",
        "site": "https://eng.ufba.br",
        "sigaa_id": "1876914"
    },
    {
        "nome": "Engenharia de Petróleo",
        "grau": "Bacharel",
        "area": "Engenharias",
        "campus": "Salvador (Federação)",
        "unidade": "Escola Politécnica (POLI)",
        "email": "petroleo@ufba.br",
        "site": "https://eng.ufba.br",
        "sigaa_id": "1876915"
    },
    {
        "nome": "Engenharia de Produção - Salvador",
        "grau": "Bacharel",
        "area": "Engenharias",
        "campus": "Salvador (Federação)",
        "unidade": "Escola Politécnica (POLI)",
        "email": "colep@ufba.br",
        "site": "https://eng.ufba.br",
        "sigaa_id": "1876916"
    },
    {
        "nome": "Engenharia de Produção - Camaçari",
        "grau": "Bacharel",
        "area": "Engenharias",
        "campus": "Camaçari (Carlos Marighella)",
        "unidade": "Instituto de Ciência, Tecnologia e Inovação (ICTI)",
        "email": "colicti@ufba.br",
        "site": "https://icti.ufba.br",
        "sigaa_id": "1877040"
    },
    {
        "nome": "Engenharia Elétrica",
        "grau": "Bacharel",
        "area": "Engenharias",
        "campus": "Salvador (Federação)",
        "unidade": "Escola Politécnica (POLI)",
        "email": "eletrica@ufba.br",
        "site": "https://eng.ufba.br",
        "sigaa_id": "1876917"
    },
    {
        "nome": "Engenharia Mecânica",
        "grau": "Bacharel",
        "area": "Engenharias",
        "campus": "Salvador (Federação)",
        "unidade": "Escola Politécnica (POLI)",
        "email": "mecanica@ufba.br",
        "site": "https://eng.ufba.br",
        "sigaa_id": "1876918"
    },
    {
        "nome": "Engenharia Química",
        "grau": "Bacharel",
        "area": "Engenharias",
        "campus": "Salvador (Federação)",
        "unidade": "Escola Politécnica (POLI)",
        "email": "engquim@ufba.br",
        "site": "https://eng.ufba.br",
        "sigaa_id": "1876919"
    },
    {
        "nome": "Engenharia Sanitária e Ambiental",
        "grau": "Bacharel",
        "area": "Engenharias",
        "campus": "Salvador (Federação)",
        "unidade": "Escola Politécnica (POLI)",
        "email": "engsanit@ufba.br",
        "site": "https://eng.ufba.br",
        "sigaa_id": "1876920"
    },
    {
        "nome": "Engenharia de Transportes",
        "grau": "Bacharel",
        "area": "Engenharias",
        "campus": "Salvador (Federação)",
        "unidade": "Escola Politécnica (POLI)",
        "email": "transpterrestre@ufba.br",
        "site": "https://eng.ufba.br",
        "sigaa_id": "1876921"
    },
    {
        "nome": "Tecnologia em Transporte Terrestre",
        "grau": "Tecnólogo",
        "area": "Engenharias",
        "campus": "Salvador (Federação)",
        "unidade": "Escola Politécnica (POLI)",
        "email": "transpterrestre@ufba.br",
        "site": "https://eng.ufba.br",
        "sigaa_id": "1876922"
    },
    {
        "nome": "BI em Ciência, Tecnologia e Inovação",
        "grau": "Bacharel",
        "area": "Engenharias",
        "campus": "Camaçari (Carlos Marighella)",
        "unidade": "Instituto de Ciência, Tecnologia e Inovação (ICTI)",
        "email": "seacicti@ufba.br",
        "site": "https://icti.ufba.br",
        "sigaa_id": "1877041"
    },
    {
        "nome": "Engenharia de Telecomunicações",
        "grau": "Bacharel",
        "area": "Engenharias",
        "campus": "Salvador (Federação)",
        "unidade": "Escola Politécnica (POLI)",
        "email": "telecom@ufba.br",
        "site": "https://eng.ufba.br",
        "sigaa_id": "1876923"
    },

    # =========================================================================
    # 3. CIÊNCIAS BIOLÓGICAS (7 cursos)
    # =========================================================================
    {
        "nome": "Ciências Biológicas - Salvador",
        "grau": "Bacharel",
        "area": "Ciências Biológicas",
        "campus": "Salvador (Ondina)",
        "unidade": "Instituto de Biologia (IBIO)",
        "email": "colbio@ufba.br",
        "site": "https://biologia.ufba.br",
        "sigaa_id": "1876861"
    },
    {
        "nome": "Ciências Biológicas - Salvador",
        "grau": "Licenciatura",
        "area": "Ciências Biológicas",
        "campus": "Salvador (Ondina)",
        "unidade": "Instituto de Biologia (IBIO)",
        "email": "colbio@ufba.br",
        "site": "https://biologia.ufba.br",
        "sigaa_id": "1876862"
    },
    {
        "nome": "Ciências Biológicas - Vitória da Conquista",
        "grau": "Bacharel",
        "area": "Ciências Biológicas",
        "campus": "Vitória da Conquista",
        "unidade": "Instituto Multidisciplinar em Saúde (IMS)",
        "email": "ims@ufba.br",
        "site": "https://ims.ufba.br",
        "sigaa_id": "1877030"
    },
    {
        "nome": "Biotecnologia - Salvador",
        "grau": "Bacharel",
        "area": "Ciências Biológicas",
        "campus": "Salvador (Ondina)",
        "unidade": "Instituto de Biologia (IBIO)",
        "email": "biotec@ufba.br",
        "site": "https://biologia.ufba.br",
        "sigaa_id": "1876863"
    },
    {
        "nome": "Biotecnologia - Vitória da Conquista",
        "grau": "Bacharel",
        "area": "Ciências Biológicas",
        "campus": "Vitória da Conquista",
        "unidade": "Instituto Multidisciplinar em Saúde (IMS)",
        "email": "ims@ufba.br",
        "site": "https://ims.ufba.br",
        "sigaa_id": "1877031"
    },
    {
        "nome": "Ciências Naturais",
        "grau": "Licenciatura",
        "area": "Ciências Biológicas",
        "campus": "Salvador (Ondina)",
        "unidade": "Instituto de Biologia (IBIO)",
        "email": "natura@ufba.br",
        "site": "https://biologia.ufba.br",
        "sigaa_id": "1876864"
    },
    {
        "nome": "Ecologia",
        "grau": "Bacharel",
        "area": "Ciências Biológicas",
        "campus": "Salvador (Ondina)",
        "unidade": "Instituto de Biologia (IBIO)",
        "email": "ecologia@ufba.br",
        "site": "https://biologia.ufba.br",
        "sigaa_id": "1876868"
    },

    # =========================================================================
    # 4. CIÊNCIAS DA SAÚDE (18 cursos)
    # =========================================================================
    {
        "nome": "Medicina - Salvador",
        "grau": "Bacharel",
        "area": "Ciências da Saúde",
        "campus": "Salvador (Terreiro de Jesus/Canela)",
        "unidade": "Faculdade de Medicina da Bahia (FMB)",
        "email": "fmb@ufba.br",
        "site": "https://fmb.ufba.br",
        "sigaa_id": "1876890"
    },
    {
        "nome": "Medicina - Vitória da Conquista",
        "grau": "Bacharel",
        "area": "Ciências da Saúde",
        "campus": "Vitória da Conquista",
        "unidade": "Instituto Multidisciplinar em Saúde (IMS)",
        "email": "colmedcat@ufba.br",
        "site": "https://ims.ufba.br",
        "sigaa_id": "1877032"
    },
    {
        "nome": "Enfermagem - Salvador",
        "grau": "Bacharel",
        "area": "Ciências da Saúde",
        "campus": "Salvador (Canela)",
        "unidade": "Escola de Enfermagem (EEUFBA)",
        "email": "enfermagem@ufba.br",
        "site": "https://enfermagem.ufba.br",
        "sigaa_id": "1876891"
    },
    {
        "nome": "Enfermagem - Vitória da Conquista",
        "grau": "Bacharel",
        "area": "Ciências da Saúde",
        "campus": "Vitória da Conquista",
        "unidade": "Instituto Multidisciplinar em Saúde (IMS)",
        "email": "ims@ufba.br",
        "site": "https://ims.ufba.br",
        "sigaa_id": "1877033"
    },
    {
        "nome": "Odontologia",
        "grau": "Bacharel",
        "area": "Ciências da Saúde",
        "campus": "Salvador (Canela)",
        "unidade": "Faculdade de Odontologia (FOUFBA)",
        "email": "odonto@ufba.br",
        "site": "https://odontologia.ufba.br",
        "sigaa_id": "1876892"
    },
    {
        "nome": "Farmácia - Salvador Diurno",
        "grau": "Bacharel",
        "area": "Ciências da Saúde",
        "campus": "Salvador (Ondina)",
        "unidade": "Faculdade de Farmácia (FFAR)",
        "email": "farmacia@ufba.br",
        "site": "https://farmacia.ufba.br",
        "sigaa_id": "1876893"
    },
    {
        "nome": "Farmácia - Salvador Noturno",
        "grau": "Bacharel",
        "area": "Ciências da Saúde",
        "campus": "Salvador (Ondina)",
        "unidade": "Faculdade de Farmácia (FFAR)",
        "email": "farmacia@ufba.br",
        "site": "https://farmacia.ufba.br",
        "sigaa_id": "1876894"
    },
    {
        "nome": "Farmácia - Vitória da Conquista",
        "grau": "Bacharel",
        "area": "Ciências da Saúde",
        "campus": "Vitória da Conquista",
        "unidade": "Instituto Multidisciplinar em Saúde (IMS)",
        "email": "ims@ufba.br",
        "site": "https://ims.ufba.br",
        "sigaa_id": "1877034"
    },
    {
        "nome": "Nutrição - Salvador",
        "grau": "Bacharel",
        "area": "Ciências da Saúde",
        "campus": "Salvador (Canela)",
        "unidade": "Escola de Nutrição (ENUT)",
        "email": "nutricao@ufba.br",
        "site": "https://nutricao.ufba.br",
        "sigaa_id": "1876895"
    },
    {
        "nome": "Nutrição - Vitória da Conquista",
        "grau": "Bacharel",
        "area": "Ciências da Saúde",
        "campus": "Vitória da Conquista",
        "unidade": "Instituto Multidisciplinar em Saúde (IMS)",
        "email": "ims@ufba.br",
        "site": "https://ims.ufba.br",
        "sigaa_id": "1877035"
    },
    {
        "nome": "Fisioterapia",
        "grau": "Bacharel",
        "area": "Ciências da Saúde",
        "campus": "Salvador (Ondina)",
        "unidade": "Instituto de Ciências da Saúde (ICS)",
        "email": "fisioterapia@ufba.br",
        "site": "https://ics.ufba.br",
        "sigaa_id": "1876896"
    },
    {
        "nome": "Fonoaudiologia",
        "grau": "Bacharel",
        "area": "Ciências da Saúde",
        "campus": "Salvador (Canela)",
        "unidade": "Instituto de Ciências da Saúde (ICS)",
        "email": "fono@ufba.br",
        "site": "https://ics.ufba.br",
        "sigaa_id": "1876897"
    },
    {
        "nome": "Terapia Ocupacional",
        "grau": "Bacharel",
        "area": "Ciências da Saúde",
        "campus": "Salvador (Canela)",
        "unidade": "Faculdade de Medicina da Bahia (FMB)",
        "email": "to@ufba.br",
        "site": "https://fmb.ufba.br",
        "sigaa_id": "1876898"
    },
    {
        "nome": "Saúde Coletiva",
        "grau": "Bacharel",
        "area": "Ciências da Saúde",
        "campus": "Salvador (Canela)",
        "unidade": "Instituto de Saúde Coletiva (ISC)",
        "email": "isc@ufba.br",
        "site": "https://isc.ufba.br",
        "sigaa_id": "1876899"
    },
    {
        "nome": "Gastronomia",
        "grau": "Bacharel",
        "area": "Ciências da Saúde",
        "campus": "Salvador (Canela)",
        "unidade": "Escola de Nutrição (ENUT)",
        "email": "gastronomia@ufba.br",
        "site": "https://nutricao.ufba.br",
        "sigaa_id": "1876900"
    },
    {
        "nome": "Educação Física",
        "grau": "Licenciatura",
        "area": "Ciências da Saúde",
        "campus": "Salvador (Ondina)",
        "unidade": "Faculdade de Educação (FACED)",
        "email": "edfisica@ufba.br",
        "site": "https://faced.ufba.br",
        "sigaa_id": "1876901"
    },
    {
        "nome": "Educação Física",
        "grau": "Bacharel",
        "area": "Ciências da Saúde",
        "campus": "Salvador (Ondina)",
        "unidade": "Faculdade de Educação (FACED)",
        "email": "edfisica@ufba.br",
        "site": "https://faced.ufba.br",
        "sigaa_id": "1876902"
    },
    {
        "nome": "BI em Saúde",
        "grau": "Bacharel",
        "area": "Ciências da Saúde",
        "campus": "Salvador (Canela/Ondina)",
        "unidade": "Instituto de Humanidades, Artes e Ciências (IHAC)",
        "email": "ihac@ufba.br",
        "site": "https://ihac.ufba.br",
        "sigaa_id": "1876931"
    },

    # =========================================================================
    # 5. CIÊNCIAS AGRÁRIAS (2 cursos)
    # =========================================================================
    {
        "nome": "Medicina Veterinária",
        "grau": "Bacharel",
        "area": "Ciências Agrárias",
        "campus": "Salvador (Ondina)",
        "unidade": "Escola de Medicina Veterinária e Zootecnia (EMEVZ)",
        "email": "medvet@ufba.br",
        "site": "https://medicinaveterinaria.ufba.br",
        "sigaa_id": "1876940"
    },
    {
        "nome": "Zootecnia",
        "grau": "Bacharel",
        "area": "Ciências Agrárias",
        "campus": "Salvador (Ondina)",
        "unidade": "Escola de Medicina Veterinária e Zootecnia (EMEVZ)",
        "email": "zootecnia@ufba.br",
        "site": "https://medicinaveterinaria.ufba.br",
        "sigaa_id": "1876941"
    },

    # =========================================================================
    # 6. CIÊNCIAS SOCIAIS APLICADAS (18 cursos)
    # =========================================================================
    {
        "nome": "Administração",
        "grau": "Bacharel",
        "area": "Ciências Sociais Aplicadas",
        "campus": "Salvador (Vale do Canela)",
        "unidade": "Escola de Administração (EADM)",
        "email": "adm@ufba.br",
        "site": "https://adm.ufba.br",
        "sigaa_id": "1876959"
    },
    {
        "nome": "Administração Pública",
        "grau": "Bacharel",
        "area": "Ciências Sociais Aplicadas",
        "campus": "EAD (Pólos UAB)",
        "unidade": "Escola de Administração (EADM)",
        "email": "admeadd@ufba.br",
        "site": "https://adm.ufba.br",
        "sigaa_id": "1877035"
    },
    {
        "nome": "Administração Pública e Gestão Social",
        "grau": "Bacharel",
        "area": "Ciências Sociais Aplicadas",
        "campus": "Salvador (Vale do Canela)",
        "unidade": "Escola de Administração (EADM)",
        "email": "apgs@ufba.br",
        "site": "https://adm.ufba.br",
        "sigaa_id": "1877038"
    },
    {
        "nome": "Gestão do Turismo e Desenvolvimento Sustentável",
        "grau": "Tecnólogo",
        "area": "Ciências Sociais Aplicadas",
        "campus": "EAD (Pólos UAB)",
        "unidade": "Escola de Administração (EADM)",
        "email": "turismoead@ufba.br",
        "site": "https://adm.ufba.br",
        "sigaa_id": "1877039"
    },
    {
        "nome": "Secretariado Executivo",
        "grau": "Bacharel",
        "area": "Ciências Sociais Aplicadas",
        "campus": "Salvador (Vale do Canela)",
        "unidade": "Escola de Administração (EADM)",
        "email": "secretariado@ufba.br",
        "site": "https://adm.ufba.br",
        "sigaa_id": "1876956"
    },
    {
        "nome": "Ciências Contábeis",
        "grau": "Bacharel",
        "area": "Ciências Sociais Aplicadas",
        "campus": "Salvador (Vale do Canela)",
        "unidade": "Faculdade de Ciências Contábeis (FCC)",
        "email": "fcc@ufba.br",
        "site": "https://fcc.ufba.br",
        "sigaa_id": "1876960"
    },
    {
        "nome": "Ciências Econômicas",
        "grau": "Bacharel",
        "area": "Ciências Sociais Aplicadas",
        "campus": "Salvador (Piedade)",
        "unidade": "Faculdade de Ciências Econômicas (FCE)",
        "email": "fce@ufba.br",
        "site": "https://fce.ufba.br",
        "sigaa_id": "1876961"
    },
    {
        "nome": "Direito",
        "grau": "Bacharel",
        "area": "Ciências Sociais Aplicadas",
        "campus": "Salvador (Graça)",
        "unidade": "Faculdade de Direito (FDUFBA)",
        "email": "direito@ufba.br",
        "site": "https://direito.ufba.br",
        "sigaa_id": "1876962"
    },
    {
        "nome": "Comunicação - Jornalismo",
        "grau": "Bacharel",
        "area": "Ciências Sociais Aplicadas",
        "campus": "Salvador (Ondina)",
        "unidade": "Faculdade de Comunicação (FACOM)",
        "email": "facom@ufba.br",
        "site": "https://facom.ufba.br",
        "sigaa_id": "1876963"
    },
    {
        "nome": "Comunicação - Produção em Comunicação e Cultura",
        "grau": "Bacharel",
        "area": "Ciências Sociais Aplicadas",
        "campus": "Salvador (Ondina)",
        "unidade": "Faculdade de Comunicação (FACOM)",
        "email": "facom@ufba.br",
        "site": "https://facom.ufba.br",
        "sigaa_id": "1876964"
    },
    {
        "nome": "Arquivologia",
        "grau": "Bacharel",
        "area": "Ciências Sociais Aplicadas",
        "campus": "Salvador (Vale do Canela)",
        "unidade": "Instituto de Ciência da Informação (ICI)",
        "email": "ici@ufba.br",
        "site": "https://ici.ufba.br",
        "sigaa_id": "1876965"
    },
    {
        "nome": "Biblioteconomia e Documentação",
        "grau": "Bacharel",
        "area": "Ciências Sociais Aplicadas",
        "campus": "Salvador (Vale do Canela)",
        "unidade": "Instituto de Ciência da Informação (ICI)",
        "email": "ici@ufba.br",
        "site": "https://ici.ufba.br",
        "sigaa_id": "1876966"
    },
    {
        "nome": "Museologia",
        "grau": "Bacharel",
        "area": "Ciências Sociais Aplicadas",
        "campus": "Salvador (Vale do Canela)",
        "unidade": "Faculdade de Filosofia e Ciências Humanas (FFCH)",
        "email": "museologia@ufba.br",
        "site": "https://ffch.ufba.br",
        "sigaa_id": "1876967"
    },
    {
        "nome": "Serviço Social",
        "grau": "Bacharel",
        "area": "Ciências Sociais Aplicadas",
        "campus": "Salvador (Federação/São Lázaro)",
        "unidade": "Instituto de Psicologia (IPSI)",
        "email": "servicosocial@ufba.br",
        "site": "https://ipsi.ufba.br",
        "sigaa_id": "1876968"
    },
    {
        "nome": "Arquitetura e Urbanismo",
        "grau": "Bacharel",
        "area": "Ciências Sociais Aplicadas",
        "campus": "Salvador (Federação)",
        "unidade": "Faculdade de Arquitetura (FAUFBA)",
        "email": "arquitet@ufba.br",
        "site": "https://arquitetura.ufba.br",
        "sigaa_id": "1876969"
    },
    {
        "nome": "Design",
        "grau": "Bacharel",
        "area": "Ciências Sociais Aplicadas",
        "campus": "Salvador (Canela)",
        "unidade": "Escola de Belas Artes (EBA)",
        "email": "design@ufba.br",
        "site": "https://belasartes.ufba.br",
        "sigaa_id": "1877020"
    },
    {
        "nome": "Design de Interiores",
        "grau": "Bacharel",
        "area": "Ciências Sociais Aplicadas",
        "campus": "Salvador (Canela)",
        "unidade": "Escola de Belas Artes (EBA)",
        "email": "interiores@ufba.br",
        "site": "https://belasartes.ufba.br",
        "sigaa_id": "1877024"
    },
    {
        "nome": "Decoração",
        "grau": "Bacharel",
        "area": "Ciências Sociais Aplicadas",
        "campus": "Salvador (Canela)",
        "unidade": "Escola de Belas Artes (EBA)",
        "email": "decoracao@ufba.br",
        "site": "https://belasartes.ufba.br",
        "sigaa_id": "1877022"
    },

    # =========================================================================
    # 7. CIÊNCIAS HUMANAS (16 cursos)
    # =========================================================================
    {
        "nome": "História",
        "grau": "Bacharel",
        "area": "Ciências Humanas",
        "campus": "Salvador (São Lázaro)",
        "unidade": "Faculdade de Filosofia e Ciências Humanas (FFCH)",
        "email": "historia@ufba.br",
        "site": "https://ffch.ufba.br",
        "sigaa_id": "1876970"
    },
    {
        "nome": "História",
        "grau": "Licenciatura",
        "area": "Ciências Humanas",
        "campus": "Salvador (São Lázaro)",
        "unidade": "Faculdade de Filosofia e Ciências Humanas (FFCH)",
        "email": "historia@ufba.br",
        "site": "https://ffch.ufba.br",
        "sigaa_id": "1876971"
    },
    {
        "nome": "Filosofia",
        "grau": "Bacharel",
        "area": "Ciências Humanas",
        "campus": "Salvador (São Lázaro)",
        "unidade": "Faculdade de Filosofia e Ciências Humanas (FFCH)",
        "email": "filosofia@ufba.br",
        "site": "https://ffch.ufba.br",
        "sigaa_id": "1876972"
    },
    {
        "nome": "Filosofia",
        "grau": "Licenciatura",
        "area": "Ciências Humanas",
        "campus": "Salvador (São Lázaro)",
        "unidade": "Faculdade de Filosofia e Ciências Humanas (FFCH)",
        "email": "filosofia@ufba.br",
        "site": "https://ffch.ufba.br",
        "sigaa_id": "1876973"
    },
    {
        "nome": "Ciências Sociais",
        "grau": "Bacharel",
        "area": "Ciências Humanas",
        "campus": "Salvador (São Lázaro)",
        "unidade": "Faculdade de Filosofia e Ciências Humanas (FFCH)",
        "email": "csociais@ufba.br",
        "site": "https://ffch.ufba.br",
        "sigaa_id": "1876974"
    },
    {
        "nome": "Ciências Sociais",
        "grau": "Licenciatura",
        "area": "Ciências Humanas",
        "campus": "Salvador (São Lázaro)",
        "unidade": "Faculdade de Filosofia e Ciências Humanas (FFCH)",
        "email": "csociais@ufba.br",
        "site": "https://ffch.ufba.br",
        "sigaa_id": "1876975"
    },
    {
        "nome": "Estudos de Gênero e Diversidade",
        "grau": "Bacharel",
        "area": "Ciências Humanas",
        "campus": "Salvador (São Lázaro)",
        "unidade": "Faculdade de Filosofia e Ciências Humanas (FFCH)",
        "email": "genero@ufba.br",
        "site": "https://ffch.ufba.br",
        "sigaa_id": "1876976"
    },
    {
        "nome": "Pedagogia - Salvador Diurno",
        "grau": "Licenciatura",
        "area": "Ciências Humanas",
        "campus": "Salvador (Vale do Canela)",
        "unidade": "Faculdade de Educação (FACED)",
        "email": "faced@ufba.br",
        "site": "https://faced.ufba.br",
        "sigaa_id": "1876977"
    },
    {
        "nome": "Pedagogia - Salvador Noturno",
        "grau": "Licenciatura",
        "area": "Ciências Humanas",
        "campus": "Salvador (Vale do Canela)",
        "unidade": "Faculdade de Educação (FACED)",
        "email": "faced@ufba.br",
        "site": "https://faced.ufba.br",
        "sigaa_id": "1876978"
    },
    {
        "nome": "Pedagogia - EAD",
        "grau": "Licenciatura",
        "area": "Ciências Humanas",
        "campus": "EAD (Pólos UAB)",
        "unidade": "Faculdade de Educação (FACED)",
        "email": "pedagogiaead@ufba.br",
        "site": "https://faced.ufba.br",
        "sigaa_id": "1877036"
    },
    {
        "nome": "Psicologia - Salvador",
        "grau": "Bacharel",
        "area": "Ciências Humanas",
        "campus": "Salvador (São Lázaro)",
        "unidade": "Instituto de Psicologia (IPSI)",
        "email": "psicologia@ufba.br",
        "site": "https://ipsi.ufba.br",
        "sigaa_id": "1876979"
    },
    {
        "nome": "Psicologia - Vitória da Conquista",
        "grau": "Bacharel",
        "area": "Ciências Humanas",
        "campus": "Vitória da Conquista",
        "unidade": "Instituto Multidisciplinar em Saúde (IMS)",
        "email": "ims@ufba.br",
        "site": "https://ims.ufba.br",
        "sigaa_id": "1877037"
    },
    {
        "nome": "BI em Humanidades - Diurno",
        "grau": "Bacharel",
        "area": "Ciências Humanas",
        "campus": "Salvador (Ondina)",
        "unidade": "Instituto de Humanidades, Artes e Ciências (IHAC)",
        "email": "ihac@ufba.br",
        "site": "https://ihac.ufba.br",
        "sigaa_id": "1876932"
    },
    {
        "nome": "BI em Humanidades - Noturno",
        "grau": "Bacharel",
        "area": "Ciências Humanas",
        "campus": "Salvador (Ondina)",
        "unidade": "Instituto de Humanidades, Artes e Ciências (IHAC)",
        "email": "ihac@ufba.br",
        "site": "https://ihac.ufba.br",
        "sigaa_id": "1876933"
    },
    {
        "nome": "Arqueologia",
        "grau": "Bacharel",
        "area": "Ciências Humanas",
        "campus": "Salvador (São Lázaro)",
        "unidade": "Faculdade de Filosofia e Ciências Humanas (FFCH)",
        "email": "arqueologia@ufba.br",
        "site": "https://ffch.ufba.br",
        "sigaa_id": "1876980"
    },
    {
        "nome": "Antropologia",
        "grau": "Bacharel",
        "area": "Ciências Humanas",
        "campus": "Salvador (São Lázaro)",
        "unidade": "Faculdade de Filosofia e Ciências Humanas (FFCH)",
        "email": "antropologia@ufba.br",
        "site": "https://ffch.ufba.br",
        "sigaa_id": "1876981"
    },

    # =========================================================================
    # 8. LINGUÍSTICA, LETRAS E ARTES (38 cursos)
    # =========================================================================
    {
        "nome": "Letras Vernáculas",
        "grau": "Bacharel",
        "area": "Linguística, Letras e Artes",
        "campus": "Salvador (Ondina)",
        "unidade": "Instituto de Letras (ILUFBA)",
        "email": "letras@ufba.br",
        "site": "https://letras.ufba.br",
        "sigaa_id": "1876982"
    },
    {
        "nome": "Letras Vernáculas",
        "grau": "Licenciatura",
        "area": "Linguística, Letras e Artes",
        "campus": "Salvador (Ondina)",
        "unidade": "Instituto de Letras (ILUFBA)",
        "email": "letras@ufba.br",
        "site": "https://letras.ufba.br",
        "sigaa_id": "1876983"
    },
    {
        "nome": "Língua Estrangeira - Inglês",
        "grau": "Licenciatura",
        "area": "Linguística, Letras e Artes",
        "campus": "Salvador (Ondina)",
        "unidade": "Instituto de Letras (ILUFBA)",
        "email": "ingles@ufba.br",
        "site": "https://letras.ufba.br",
        "sigaa_id": "1876984"
    },
    {
        "nome": "Língua Estrangeira - Espanhol",
        "grau": "Licenciatura",
        "area": "Linguística, Letras e Artes",
        "campus": "Salvador (Ondina)",
        "unidade": "Instituto de Letras (ILUFBA)",
        "email": "espanhol@ufba.br",
        "site": "https://letras.ufba.br",
        "sigaa_id": "1876985"
    },
    {
        "nome": "Língua Estrangeira - Francês",
        "grau": "Licenciatura",
        "area": "Linguística, Letras e Artes",
        "campus": "Salvador (Ondina)",
        "unidade": "Instituto de Letras (ILUFBA)",
        "email": "frances@ufba.br",
        "site": "https://letras.ufba.br",
        "sigaa_id": "1876986"
    },
    {
        "nome": "Língua Estrangeira - Alemão",
        "grau": "Licenciatura",
        "area": "Linguística, Letras e Artes",
        "campus": "Salvador (Ondina)",
        "unidade": "Instituto de Letras (ILUFBA)",
        "email": "alemao@ufba.br",
        "site": "https://letras.ufba.br",
        "sigaa_id": "1876987"
    },
    {
        "nome": "Língua Estrangeira - Italiano",
        "grau": "Licenciatura",
        "area": "Linguística, Letras e Artes",
        "campus": "Salvador (Ondina)",
        "unidade": "Instituto de Letras (ILUFBA)",
        "email": "italiano@ufba.br",
        "site": "https://letras.ufba.br",
        "sigaa_id": "1876988"
    },
    {
        "nome": "Línguas Clássicas - Grego e Latim",
        "grau": "Bacharel",
        "area": "Linguística, Letras e Artes",
        "campus": "Salvador (Ondina)",
        "unidade": "Instituto de Letras (ILUFBA)",
        "email": "classicas@ufba.br",
        "site": "https://letras.ufba.br",
        "sigaa_id": "1876989"
    },
    {
        "nome": "Letras - Tradução",
        "grau": "Bacharel",
        "area": "Linguística, Letras e Artes",
        "campus": "Salvador (Ondina)",
        "unidade": "Instituto de Letras (ILUFBA)",
        "email": "traducao@ufba.br",
        "site": "https://letras.ufba.br",
        "sigaa_id": "1876990"
    },
    {
        "nome": "Artes Visuais",
        "grau": "Licenciatura",
        "area": "Linguística, Letras e Artes",
        "campus": "Salvador (Canela)",
        "unidade": "Escola de Belas Artes (EBA)",
        "email": "artesvisuais@ufba.br",
        "site": "https://belasartes.ufba.br",
        "sigaa_id": "1877001"
    },
    {
        "nome": "Artes Plásticas",
        "grau": "Bacharel",
        "area": "Linguística, Letras e Artes",
        "campus": "Salvador (Canela)",
        "unidade": "Escola de Belas Artes (EBA)",
        "email": "artesplasticas@ufba.br",
        "site": "https://belasartes.ufba.br",
        "sigaa_id": "1877002"
    },
    {
        "nome": "Desenho e Plástica",
        "grau": "Licenciatura",
        "area": "Linguística, Letras e Artes",
        "campus": "Salvador (Canela)",
        "unidade": "Escola de Belas Artes (EBA)",
        "email": "desenho@ufba.br",
        "site": "https://belasartes.ufba.br",
        "sigaa_id": "1877010"
    },
    {
        "nome": "Dança - Diurno",
        "grau": "Bacharel",
        "area": "Linguística, Letras e Artes",
        "campus": "Salvador (Ondina)",
        "unidade": "Escola de Dança (EDAN)",
        "email": "danca@ufba.br",
        "site": "https://danca.ufba.br",
        "sigaa_id": "1877011"
    },
    {
        "nome": "Dança - Diurno",
        "grau": "Licenciatura",
        "area": "Linguística, Letras e Artes",
        "campus": "Salvador (Ondina)",
        "unidade": "Escola de Dança (EDAN)",
        "email": "danca@ufba.br",
        "site": "https://danca.ufba.br",
        "sigaa_id": "1877012"
    },
    {
        "nome": "Dança - Noturno",
        "grau": "Licenciatura",
        "area": "Linguística, Letras e Artes",
        "campus": "Salvador (Ondina)",
        "unidade": "Escola de Dança (EDAN)",
        "email": "danca@ufba.br",
        "site": "https://danca.ufba.br",
        "sigaa_id": "1877013"
    },
    {
        "nome": "Dança - EAD",
        "grau": "Licenciatura",
        "area": "Linguística, Letras e Artes",
        "campus": "EAD (Pólos UAB)",
        "unidade": "Escola de Dança (EDAN)",
        "email": "dancaead@ufba.br",
        "site": "https://danca.ufba.br",
        "sigaa_id": "1877014"
    },
    {
        "nome": "Teatro",
        "grau": "Licenciatura",
        "area": "Linguística, Letras e Artes",
        "campus": "Salvador (Canela)",
        "unidade": "Escola de Teatro (ETUFBA)",
        "email": "teatro@ufba.br",
        "site": "https://teatro.ufba.br",
        "sigaa_id": "1877015"
    },
    {
        "nome": "Artes Cênicas - Interpretação Teatral",
        "grau": "Bacharel",
        "area": "Linguística, Letras e Artes",
        "campus": "Salvador (Canela)",
        "unidade": "Escola de Teatro (ETUFBA)",
        "email": "teatro@ufba.br",
        "site": "https://teatro.ufba.br",
        "sigaa_id": "1877016"
    },
    {
        "nome": "Artes Cênicas - Direção Teatral",
        "grau": "Bacharel",
        "area": "Linguística, Letras e Artes",
        "campus": "Salvador (Canela)",
        "unidade": "Escola de Teatro (ETUFBA)",
        "email": "teatro@ufba.br",
        "site": "https://teatro.ufba.br",
        "sigaa_id": "1877017"
    },
    {
        "nome": "Artes Cênicas - Cenografia",
        "grau": "Bacharel",
        "area": "Linguística, Letras e Artes",
        "campus": "Salvador (Canela)",
        "unidade": "Escola de Teatro (ETUFBA)",
        "email": "teatro@ufba.br",
        "site": "https://teatro.ufba.br",
        "sigaa_id": "1877018"
    },
    {
        "nome": "Teatro - EAD",
        "grau": "Licenciatura",
        "area": "Linguística, Letras e Artes",
        "campus": "EAD (Pólos UAB)",
        "unidade": "Escola de Teatro (ETUFBA)",
        "email": "teatroead@ufba.br",
        "site": "https://teatro.ufba.br",
        "sigaa_id": "1877019"
    },
    {
        "nome": "Música",
        "grau": "Licenciatura",
        "area": "Linguística, Letras e Artes",
        "campus": "Salvador (Canela)",
        "unidade": "Escola de Música (EMUS)",
        "email": "musica@ufba.br",
        "site": "https://musica.ufba.br",
        "sigaa_id": "1877025"
    },
    {
        "nome": "Música - EAD",
        "grau": "Licenciatura",
        "area": "Linguística, Letras e Artes",
        "campus": "EAD (Pólos UAB)",
        "unidade": "Escola de Música (EMUS)",
        "email": "musicaead@ufba.br",
        "site": "https://musica.ufba.br",
        "sigaa_id": "1877026"
    },
    {
        "nome": "Canto",
        "grau": "Bacharel",
        "area": "Linguística, Letras e Artes",
        "campus": "Salvador (Canela)",
        "unidade": "Escola de Música (EMUS)",
        "email": "canto@ufba.br",
        "site": "https://musica.ufba.br",
        "sigaa_id": "1877027"
    },
    {
        "nome": "Composição e Regência",
        "grau": "Bacharel",
        "area": "Linguística, Letras e Artes",
        "campus": "Salvador (Canela)",
        "unidade": "Escola de Música (EMUS)",
        "email": "composicao@ufba.br",
        "site": "https://musica.ufba.br",
        "sigaa_id": "1877028"
    },
    {
        "nome": "Instrumento - Piano",
        "grau": "Bacharel",
        "area": "Linguística, Letras e Artes",
        "campus": "Salvador (Canela)",
        "unidade": "Escola de Música (EMUS)",
        "email": "instrumento@ufba.br",
        "site": "https://musica.ufba.br",
        "sigaa_id": "1877029"
    },
    {
        "nome": "Instrumento - Violão",
        "grau": "Bacharel",
        "area": "Linguística, Letras e Artes",
        "campus": "Salvador (Canela)",
        "unidade": "Escola de Música (EMUS)",
        "email": "instrumento@ufba.br",
        "site": "https://musica.ufba.br",
        "sigaa_id": "1877042"
    },
    {
        "nome": "Instrumento - Violino",
        "grau": "Bacharel",
        "area": "Linguística, Letras e Artes",
        "campus": "Salvador (Canela)",
        "unidade": "Escola de Música (EMUS)",
        "email": "instrumento@ufba.br",
        "site": "https://musica.ufba.br",
        "sigaa_id": "1877043"
    },
    {
        "nome": "Instrumento - Violoncelo",
        "grau": "Bacharel",
        "area": "Linguística, Letras e Artes",
        "campus": "Salvador (Canela)",
        "unidade": "Escola de Música (EMUS)",
        "email": "instrumento@ufba.br",
        "site": "https://musica.ufba.br",
        "sigaa_id": "1877044"
    },
    {
        "nome": "Instrumento - Flauta",
        "grau": "Bacharel",
        "area": "Linguística, Letras e Artes",
        "campus": "Salvador (Canela)",
        "unidade": "Escola de Música (EMUS)",
        "email": "instrumento@ufba.br",
        "site": "https://musica.ufba.br",
        "sigaa_id": "1877045"
    },
    {
        "nome": "Instrumento - Clarinete",
        "grau": "Bacharel",
        "area": "Linguística, Letras e Artes",
        "campus": "Salvador (Canela)",
        "unidade": "Escola de Música (EMUS)",
        "email": "instrumento@ufba.br",
        "site": "https://musica.ufba.br",
        "sigaa_id": "1877046"
    },
    {
        "nome": "Instrumento - Trompete",
        "grau": "Bacharel",
        "area": "Linguística, Letras e Artes",
        "campus": "Salvador (Canela)",
        "unidade": "Escola de Música (EMUS)",
        "email": "instrumento@ufba.br",
        "site": "https://musica.ufba.br",
        "sigaa_id": "1877047"
    },
    {
        "nome": "Instrumento - Percussão",
        "grau": "Bacharel",
        "area": "Linguística, Letras e Artes",
        "campus": "Salvador (Canela)",
        "unidade": "Escola de Música (EMUS)",
        "email": "instrumento@ufba.br",
        "site": "https://musica.ufba.br",
        "sigaa_id": "1877048"
    },
    {
        "nome": "Música Popular",
        "grau": "Bacharel",
        "area": "Linguística, Letras e Artes",
        "campus": "Salvador (Canela)",
        "unidade": "Escola de Música (EMUS)",
        "email": "musicapopular@ufba.br",
        "site": "https://musica.ufba.br",
        "sigaa_id": "1877049"
    },
    {
        "nome": "BI em Artes - Diurno",
        "grau": "Bacharel",
        "area": "Linguística, Letras e Artes",
        "campus": "Salvador (Ondina)",
        "unidade": "Instituto de Humanidades, Artes e Ciências (IHAC)",
        "email": "ihac@ufba.br",
        "site": "https://ihac.ufba.br",
        "sigaa_id": "1876934"
    },
    {
        "nome": "BI em Artes - Noturno",
        "grau": "Bacharel",
        "area": "Linguística, Letras e Artes",
        "campus": "Salvador (Ondina)",
        "unidade": "Instituto de Humanidades, Artes e Ciências (IHAC)",
        "email": "ihac@ufba.br",
        "site": "https://ihac.ufba.br",
        "sigaa_id": "1876935"
    },
    {
        "nome": "Produção Cultural",
        "grau": "Bacharel",
        "area": "Linguística, Letras e Artes",
        "campus": "Salvador (Canela)",
        "unidade": "Escola de Teatro / Belas Artes",
        "email": "prodcultural@ufba.br",
        "site": "https://ufba.br",
        "sigaa_id": "1877050"
    },
    {
        "nome": "Conservação e Restauração",
        "grau": "Bacharel",
        "area": "Linguística, Letras e Artes",
        "campus": "Salvador (Canela)",
        "unidade": "Escola de Belas Artes (EBA)",
        "email": "restauracao@ufba.br",
        "site": "https://belasartes.ufba.br",
        "sigaa_id": "1877051"
    }
]

AREAS_CONHECIMENTO = [
    "Ciências Exatas e da Terra",
    "Ciências Biológicas",
    "Engenharias",
    "Ciências da Saúde",
    "Ciências Agrárias",
    "Ciências Sociais Aplicadas",
    "Ciências Humanas",
    "Linguística, Letras e Artes"
]

PASTA_GERAL = "UFBA - Geral"

def get_folder_name(course_info: dict) -> str:
    """Retorna o nome padronizado da pasta para o curso: 'Nome (Grau)'."""
    return f"{course_info['nome']} ({course_info['grau']})"


def get_course_dir(base_dir, course_info: dict):
    from pathlib import Path
    base = Path(base_dir)
    return base / "Experimento" / "Áreas do conhecimento" / course_info["area"] / get_folder_name(course_info)

