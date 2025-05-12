import requests

# Municipios
url_muni = "https://public.opendatasoft.com/explore/dataset/georef-spain-municipio/download/?format=geojson&lang=es&timezone=Europe%2FMadrid"
r_muni = requests.get(url_muni)
# Guardar directamente en el CWD, que será ETL/GeoRef_Spain/
with open("georef-spain-municipio.geojson", "wb") as f:
    f.write(r_muni.content)

# Comunidades Autónomas
url_ccaa = "https://public.opendatasoft.com/explore/dataset/georef-spain-comunidad-autonoma/download/?format=geojson&lang=es"
r_ccaa = requests.get(url_ccaa)
# Guardar directamente en el CWD, que será ETL/GeoRef_Spain/
with open("georef-spain-comunidad-autonoma.geojson", "wb") as f:
    f.write(r_ccaa.content)

print("Descarga completada.")
