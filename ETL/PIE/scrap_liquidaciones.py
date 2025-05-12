import os
import requests

# Lista de URLs extraídas automáticamente
URLS = [
    "https://www.hacienda.gob.es/CDI/Sist%20Financiacion%20y%20Deuda/InformacionEELLs/2024/LiquidacionVariable2022.xlsx",
    "https://www.hacienda.gob.es/CDI/Sist%20Financiacion%20y%20Deuda/InformacionEELLs/2021/LiquidacionVariable2021.xls",
    "https://www.hacienda.gob.es/CDI/Sist%20Financiacion%20y%20Deuda/InformacionEELLs/2022/LiquidacionVariable2020.xls",
    "https://www.hacienda.gob.es/CDI/Sist%20Financiacion%20y%20Deuda/InformacionEELLs/2019/LiquidacionVariable2019.xls",
    "https://www.hacienda.gob.es/CDI/Sist%20Financiacion%20y%20Deuda/InformacionEELLs/2018/LiquidacionVariable2018.xls",
    "https://www.hacienda.gob.es/CDI/Sist%20Financiacion%20y%20Deuda/InformacionEELLs/2017/LiquidacionVariables2017.xls",
    "https://www.hacienda.gob.es/CDI/Sist%20Financiacion%20y%20Deuda/InformacionEELLs/2017/Variables-2017-WEB-con-SII-IVA.xlsx",
    "https://www.hacienda.gob.es/Documentacion/Publico/CDI/Sist%20Financiacion%20y%20Deuda/InformacionEELLs/2016/Liquidaci%C3%B3nVariable2016.xls",
    "https://www.hacienda.gob.es/Documentacion/Publico/CDI/Sist%20Financiacion%20y%20Deuda/InformacionEELLs/2015/LiquidacionVariable2015.xls",
    "https://www.hacienda.gob.es/Documentacion/Publico/CDI/Sist%20Financiacion%20y%20Deuda/InformacionEELLs/2014/LiquidacionVariable2014.xls",
    "https://www.hacienda.gob.es/Documentacion/Publico/CDI/Sist%20Financiacion%20y%20Deuda/InformacionEELLs/2014/LiquidacionVariable2014jul.xls",
    "https://www.hacienda.gob.es/Documentacion/Publico/DGCFEL/LiquidacionesDefinitivas/Liquidacion%20definitiva%202013.Variables.xls",
    "https://www.hacienda.gob.es/Documentacion/Publico/DGCFEL/LiquidacionesDefinitivas/Liquidacion%20definitiva%202012%20Variables%20DEFINITIVO.xls",
    "https://www.hacienda.gob.es/Documentacion/Publico/DGCFEL/LiquidacionesDefinitivas/Liquidacion%20definitiva%202011.Variables.xls",
    "https://www.hacienda.gob.es/Documentacion/Publico/DGCFEL/LiquidacionesDefinitivas/Liquidacion%20definitiva%202010.Variables.xls",
    "https://www.hacienda.gob.es/Documentacion/Publico/DGCFEL/LiquidacionesDefinitivas/Liquidacion%20definitiva%202009.Variables.xls",
    "https://www.hacienda.gob.es/Documentacion/Publico/DGCFEL/LiquidacionesDefinitivas/Liquidacion%20definitiva%202008.Variables.xls",
    "https://www.hacienda.gob.es/Documentacion/Publico/DGCFEL/LiquidacionesDefinitivas/Liquidacion%20definitiva%202007.Variables.xls",
    "https://www.hacienda.gob.es/Documentacion/Publico/AdministracionElectronica/Oficina%20Virtual%20Entidades%20Locales/Liquidacion2006DatosWeb.xls",
    "https://www.hacienda.gob.es/Documentacion/Publico/AdministracionElectronica/Oficina%20Virtual%20Entidades%20Locales/Liquidacion2005DatosWeb.xls",
    "https://www.hacienda.gob.es/Documentacion/Publico/DGCFEL/Liquidacion2004DatosWeb.xls",
    "https://www.hacienda.gob.es/SGFAL/DGCFEL/Noticias/PTE%202003.xls"
]

DEST_DIR = "./ETL/PIE/data/raw/finanzas/liquidaciones"
os.makedirs(DEST_DIR, exist_ok=True)

for url in URLS:
    filename = url.split("/")[-1]
    dest_path = os.path.join(DEST_DIR, filename)
    print(f"Descargando {filename} ...")
    try:
        resp = requests.get(url, timeout=60)
        resp.raise_for_status()
        with open(dest_path, "wb") as f:
            f.write(resp.content)
        print(f"Guardado en {dest_path}")
    except Exception as e:
        print(f"Error descargando {url}: {e}")
