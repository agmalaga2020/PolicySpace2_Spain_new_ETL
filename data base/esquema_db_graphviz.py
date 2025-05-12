from graphviz import Digraph

dot = Digraph('ER_Diagram_Record', engine='dot', format='png')
dot.attr(rankdir='LR')
dot.attr('node', fontname='Helvetica', fontsize='10')

# Nodos de tablas en estilo record
dot.node('tabla_equivalencias',
         label='{tabla_equivalencias|CODAUTO TEXT PK\lCPRO TEXT\lCMUN TEXT\lDC TEXT\lNOMBRE TEXT\lmun_code TEXT\l}',
         shape='record')
dot.node('cifras_poblacion_municipio',
         label='{cifras_poblacion_municipio|mun_code TEXT PK\l1996 FLOAT\l1998 FLOAT\l1999 FLOAT\l2000 FLOAT\l2001 FLOAT\l2002 FLOAT\l2003 FLOAT\l2004 FLOAT\l2005 FLOAT\l2006 FLOAT\l2007 FLOAT\l2008 FLOAT\l2009 FLOAT\l2010 FLOAT\l2011 FLOAT\l2012 FLOAT\l2013 FLOAT\l2014 FLOAT\l2015 FLOAT\l2016 FLOAT\l2017 FLOAT\l2018 FLOAT\l2019 FLOAT\l2020 FLOAT\l2021 FLOAT\l2022 FLOAT\l2023 FLOAT\l2024 FLOAT\lnum_outliers BIGINT\l}',
         shape='record')
dot.node('df_mortalidad_ccaa_sexo',
         label='{df_mortalidad_ccaa_sexo|ccaa_code TEXT\lccaa_name TEXT\lEdad BIGINT\lyear BIGINT\lsex TEXT\ltotal_muertes FLOAT\l}',
         shape='record')
dot.node('distribucion_urbana',
         label='{distribucion_urbana|mun_code TEXT\lyear TEXT\lproporcion_urbana FLOAT\l}',
         shape='record')
dot.node('empresas_municipio_actividad_principal',
         label='{empresas_municipio_actividad_principal|mun_code TEXT\lmunicipio_name TEXT\lyear BIGINT\ltotal_empresas FLOAT\l}',
         shape='record')
dot.node('estimativas_pop',
         label='{estimativas_pop|mun_code TEXT PK\l1996–2024 FLOAT each\l}',
         shape='record')
dot.node('idhm_indice_desarrollo_humano_municipal',
         label='{idhm_indice_desarrollo_humano_municipal|year BIGINT\lcodigo_aeat BIGINT\lpopulation FLOAT\lrenta_bruta_total FLOAT\lrenta_disponible_total FLOAT\lrenta_disponible_per_capita FLOAT\lmun_code TEXT\lNOMBRE TEXT\lCODAUTO BIGINT\lEV0 FLOAT\lI_salud FLOAT\lI_educ FLOAT\lI_ingresos FLOAT\lIDHM FLOAT\l}',
         shape='record')
dot.node('indicadores_fecundidad_municipio_provincias',
         label='{indicadores_fecundidad_municipio_provincias|provincias_name TEXT\lyear TEXT\ledad TEXT\ltotal_interpolado TEXT\lCODAUTO TEXT\lComunidad Autónoma TEXT\ltasa_fert_prov TEXT\lcpro TEXT\l}',
         shape='record')
dot.node('interest_data_ETL',
         label='{interest_data_ETL|date DATETIME PK\linterest_fixed FLOAT\lmortgage_x FLOAT\linterest_nominal FLOAT\lmortgage_y FLOAT\linterest_real FLOAT\lmortgage FLOAT\l}',
         shape='record')
dot.node('nivel_educativo_comunidades',
         label='{nivel_educativo_comunidades|ccaa_code TEXT\lccaa_name TEXT\laño BIGINT\nivel_formacion TEXT\nmedia_total FLOAT\nnivel_formacion_code FLOAT\l}',
         shape='record')
dot.node('PIE',
         label='{PIE|codigo_provincia FLOAT\nmun_code TEXT\nnombre_municipio TEXT\ntotal_participacion_variables FLOAT\nyear BIGINT\npoblacion FLOAT\nesfuerzo_fiscal FLOAT\ninverso_capacidad_tributaria FLOAT\l}',
         shape='record')
dot.node('vista_equivalencias_unicas',
         label='{vista_equivalencias_unicas|CMUN TEXT PK\lNOMBRE TEXT\lCPRO TEXT\l}',
         shape='record')

# Relaciones
dot.edge('tabla_equivalencias', 'cifras_poblacion_municipio', label='mun_code')
dot.edge('cifras_poblacion_municipio', 'distribucion_urbana', label='mun_code')
dot.edge('cifras_poblacion_municipio', 'empresas_municipio_actividad_principal', label='mun_code')
dot.edge('cifras_poblacion_municipio', 'estimativas_pop', label='mun_code')
dot.edge('cifras_poblacion_municipio', 'idhm_indice_desarrollo_humano_municipal', label='mun_code')
dot.edge('cifras_poblacion_municipio', 'PIE', label='mun_code')
dot.edge('tabla_equivalencias', 'vista_equivalencias_unicas', label='CMUN')
dot.edge('tabla_equivalencias', 'indicadores_fecundidad_municipio_provincias', label='CODAUTO/CPRO')
dot.edge('nivel_educativo_comunidades', 'df_mortalidad_ccaa_sexo', label='ccaa_code')
dot.edge('indicadores_fecundidad_municipio_provincias', 'idhm_indice_desarrollo_humano_municipal', label='CODAUTO')

# Render
output_path = dot.render('esquema_db_record')
print("Diagrama guardado en:", output_path)
