import streamlit as st

st.title("ℹ️ Documentación del Proyecto")

doc_tab1, doc_tab2 = st.tabs(["📖 Visión General", "📑 Categorización de Datos"])

# Pestaña Visión General
with doc_tab1:
    st.header("Visión General del Proyecto")
    
    # Sección de Introducción
    st.subheader("🎯 Objetivo")
    st.markdown("""
    Adaptar el proyecto PolicySpace2 al mercado español, recopilando datos equivalentes 
    a los utilizados en el contexto brasileño original.
    """)
    
    # Fuentes de Datos
    st.subheader("📊 Fuentes de Datos")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        #### INE
        **Instituto Nacional de Estadística**
        
        Proporciona datos demográficos, económicos y sociales oficiales de España a través de su API JSON.
        
        [Acceder a la API](https://www.ine.es/dyngs/DAB/index.htm?cid=1099)
        """)
        
    with col2:
        st.markdown("""
        #### DataBank
        **Banco Mundial**
        
        Proporciona indicadores económicos y de desarrollo para España y otros países.
        
        [Acceder a DataBank](https://datos.bancomundial.org/)
        """)
        
    with col3:
        st.markdown("""
        #### Ministerio de Hacienda
        **Gobierno de España**
        
        Proporciona datos de financiación municipal y otros indicadores fiscales.
        
        [Ver datos](https://www.hacienda.gob.es/)
        """)

# Pestaña Categorización de Datos
with doc_tab2:
    st.header("Categorización de Datos")
    
    # Añadir contenido del archivo categorias_documentos.md
    with open("home/ubuntu/categorias_documentos.md", "r", encoding="utf-8") as f:
        contenido_md = f.read()
        st.markdown(contenido_md)
