import subprocess
import os
from tqdm import tqdm

# Define the base directory where this script and the target scripts are located
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Define the sequence of scripts to execute
scripts_a_ejecutar = [
    'download_georef_spain.py',
    'mapear_coordenadas.py',
    'mapear_coordenadas_comunidades.py',
    'visualizar_mapa_municipios.py',
    'visualizar_mapa_poligonos_comunidades.py',
    'visualizar_mapa_poligonos_municipios.py'
]

def ejecutar_script(script_name):
    """Ejecuta un script de Python y devuelve True si tiene éxito, False en caso contrario."""
    script_path = os.path.join(BASE_DIR, script_name)
    
    if not os.path.exists(script_path):
        print(f"\nError: El script '{script_path}' no fue encontrado.")
        return False
        
    try:
        # Usamos Popen para capturar la salida en tiempo real si fuera necesario en el futuro,
        # pero por ahora, run es suficiente y más simple.
        # Se usa check=True para que lance CalledProcessError si el script falla (exit code != 0)
        # Se captura stdout y stderr para evitar que se impriman directamente a menos que haya un error.
        proceso = subprocess.run(['python', script_path], 
                                 capture_output=True, 
                                 text=True, 
                                 check=True, 
                                 cwd=BASE_DIR) # Ejecutar cada script en su propio directorio
        # print(f"Salida de {script_name}:\n{proceso.stdout}") # Descomentar si se necesita ver la salida normal
        return True
    except subprocess.CalledProcessError as e:
        print(f"\nError al ejecutar el script '{script_name}'.")
        print(f"Código de retorno: {e.returncode}")
        print(f"Salida estándar (stdout):\n{e.stdout}")
        print(f"Error estándar (stderr):\n{e.stderr}")
        return False
    except FileNotFoundError:
        print(f"\nError: El intérprete 'python' no fue encontrado o el script '{script_path}' no existe.")
        return False
    except Exception as e:
        print(f"\nOcurrió un error inesperado al ejecutar '{script_name}': {e}")
        return False

def main():
    print("Iniciando la ejecución del flujo completo de scripts GeoRef Spain...")
    
    # Usamos tqdm para la barra de progreso
    with tqdm(total=len(scripts_a_ejecutar), desc="Progreso del Flujo GeoRef") as pbar:
        for i, script_nombre in enumerate(scripts_a_ejecutar):
            pbar.set_description(f"Ejecutando: {script_nombre}")
            print(f"\n--- Paso {i+1}/{len(scripts_a_ejecutar)}: Ejecutando {script_nombre} ---")
            
            exito = ejecutar_script(script_nombre)
            
            if exito:
                print(f"Éxito: El script '{script_nombre}' se ejecutó correctamente.")
            else:
                print(f"Fracaso: El script '{script_nombre}' falló. Deteniendo el flujo.")
                break # Detener si un script falla
            
            pbar.update(1)
            
    if pbar.n == len(scripts_a_ejecutar):
        print("\n¡Flujo completo de scripts GeoRef Spain ejecutado con éxito!")
    else:
        print("\nEl flujo de scripts GeoRef Spain se interrumpió debido a un error.")

if __name__ == "__main__":
    main()
