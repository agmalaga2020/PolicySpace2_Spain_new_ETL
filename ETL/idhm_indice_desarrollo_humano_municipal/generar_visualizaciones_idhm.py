# -*- coding: utf-8 -*-
"""
generar_visualizaciones_idhm.py

Generates visualizations based on the final IDHM calculation results.
Reads the 'IRPFmunicipios_final_IDHM.csv' file and saves plots
as image files in a subfolder.

Adapted for local execution (Visual Studio Code, plain Python).
-------------------------------------------------------------------------
- Uses script-relative paths: Reads the input CSV from the same directory
  as this script and saves plots to a subfolder (`visualizaciones_idhm`)
  created within the script's directory.
- Requires the final IDHM data file to exist in the same directory.
- Requires matplotlib and numpy to be installed (`pip install matplotlib numpy pandas`).

Run from anywhere after the main script has run successfully:
    $ python path/to/generar_visualizaciones_idhm.py
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path
import warnings

# Suppress potential warnings from matplotlib or pandas if needed
warnings.filterwarnings("ignore", category=UserWarning)

# --- Configuration ---
INPUT_FILENAME = "IRPFmunicipios_final_IDHM.csv"
OUTPUT_FOLDER_NAME = "visualizaciones_idhm"

# --- Helper Functions ---

def get_script_directory() -> Path:
    """Returns the absolute path to the directory containing this script."""
    return Path(__file__).parent.resolve()

def create_output_folder(base_dir: Path, folder_name: str) -> Path:
    """Creates the output folder if it doesn't exist."""
    output_path = base_dir / folder_name
    try:
        output_path.mkdir(parents=True, exist_ok=True)
        print(f"Output folder ensured: '{output_path}'")
        return output_path
    except OSError as e:
        print(f"❌ Error creating output folder '{output_path}': {e}")
        return None

def save_plot(output_folder: Path, filename: str):
    """Saves the current matplotlib plot to the specified folder and closes it."""
    if output_folder is None:
        print(f"⚠️ Cannot save plot '{filename}', output folder not available.")
        plt.close() # Close plot even if saving failed
        return

    filepath = output_folder / filename
    try:
        plt.savefig(filepath, dpi=150, bbox_inches='tight') # Save with good resolution
        print(f"  Plot saved to: '{filepath.name}'")
        plt.close() # Close the figure to free memory
    except Exception as e:
        print(f"❌ Error saving plot '{filepath.name}': {e}")
        plt.close() # Still close the plot

# --- Main Plotting Logic ---

def main():
    """Loads data and generates all visualizations."""
    print("--- Starting IDHM Visualization Script ---")
    script_dir = get_script_directory()
    input_file_path = script_dir / INPUT_FILENAME

    # 1. Load Data
    print(f"Loading data from: '{input_file_path}'")
    try:
        df = pd.read_csv(input_file_path)
        print("Data loaded successfully.")
    except FileNotFoundError:
        print(f"❌ Error: Input file not found at '{input_file_path}'.")
        print("Please ensure the main IDHM calculation script ran successfully first.")
        return
    except Exception as e:
        print(f"❌ Error loading data: {e}")
        return

    # 2. Create Output Folder
    output_folder = create_output_folder(script_dir, OUTPUT_FOLDER_NAME)
    if output_folder is None:
        print("❌ Exiting: Could not create output folder.")
        return

    print("\nGenerating plots...")

    # === Plot Group 1: Basic Distributions and Trends ===

    # Plot 1.1: Histogram of IDHM for the latest year (e.g., 2022)
    latest_year = df["year"].max()
    df_latest = df[df["year"] == latest_year]
    if not df_latest.empty:
        plt.figure(figsize=(8, 5))
        plt.hist(df_latest["IDHM"].dropna(), bins=30, edgecolor='black') # dropna just in case
        plt.title(f"Distribución de IDHM en municipios ({latest_year})")
        plt.xlabel("IDHM")
        plt.ylabel("Frecuencia")
        plt.grid(axis='y', linestyle='--', alpha=0.7)
        save_plot(output_folder, f"histogram_idhm_{latest_year}.png")
    else:
        print(f"⚠️ Skipping histogram: No data found for year {latest_year}.")

    # Plot 1.2: Time series of average national IDHM
    if not df.empty:
        df_mean_year = df.groupby("year")["IDHM"].mean().reset_index()
        plt.figure(figsize=(9, 5))
        plt.plot(df_mean_year["year"], df_mean_year["IDHM"], marker='o', linestyle='-')
        plt.title("IDHM promedio nacional por año")
        plt.xlabel("Año")
        plt.ylabel("IDHM promedio")
        plt.xticks(df_mean_year["year"].unique()) # Ensure all years are shown if few
        plt.grid(True, linestyle='--', alpha=0.7)
        save_plot(output_folder, "timeseries_idhm_national_avg.png")
    else:
        print("⚠️ Skipping national average plot: No data loaded.")

    # === Plot Group 2: Scatter Plots between Sub-indices (Latest Year) ===
    if not df_latest.empty:
        print(f"\nGenerating scatter plots for {latest_year}...")
        # Plot 2.1: I_ingresos vs I_educ
        plt.figure(figsize=(7, 6))
        plt.scatter(df_latest["I_ingresos"], df_latest["I_educ"], alpha=0.5, s=15)
        plt.xlabel("I_ingresos")
        plt.ylabel("I_educ")
        plt.title(f"Ingresos vs Educación ({latest_year})")
        plt.grid(True, linestyle='--', alpha=0.5)
        save_plot(output_folder, f"scatter_income_vs_educ_{latest_year}.png")

        # Plot 2.2: I_salud vs I_ingresos
        plt.figure(figsize=(7, 6))
        plt.scatter(df_latest["I_ingresos"], df_latest["I_salud"], alpha=0.5, s=15)
        plt.xlabel("I_ingresos")
        plt.ylabel("I_salud")
        plt.title(f"Ingresos vs Salud ({latest_year})")
        plt.grid(True, linestyle='--', alpha=0.5)
        save_plot(output_folder, f"scatter_income_vs_health_{latest_year}.png")

        # Plot 2.3: I_salud vs I_educ
        plt.figure(figsize=(7, 6))
        plt.scatter(df_latest["I_educ"], df_latest["I_salud"], alpha=0.5, s=15)
        plt.xlabel("I_educ")
        plt.ylabel("I_salud")
        plt.title(f"Educación vs Salud ({latest_year})")
        plt.grid(True, linestyle='--', alpha=0.5)
        save_plot(output_folder, f"scatter_educ_vs_health_{latest_year}.png")
    else:
         print(f"⚠️ Skipping sub-index scatter plots: No data for year {latest_year}.")

    # === Plot Group 3: Deeper Analysis Plots ===
    if not df_latest.empty and 'population' in df_latest.columns and 'CODAUTO' in df_latest.columns:
        print(f"\nGenerating advanced analysis plots for {latest_year}...")
        df_latest = df_latest.copy() # Avoid SettingWithCopyWarning

        # Plot 3.1: Population vs IDHM (log scale)
        # Filter out zero or negative population before log
        pop_positive = df_latest[df_latest["population"] > 0]
        if not pop_positive.empty:
            plt.figure(figsize=(8, 6))
            plt.scatter(np.log10(pop_positive["population"]), pop_positive["IDHM"], alpha=0.6, s=20)
            plt.xlabel("Log10(Población)")
            plt.ylabel(f"IDHM ({latest_year})")
            plt.title(f"Relación entre tamaño poblacional e IDHM ({latest_year})")
            plt.grid(True, linestyle='--', alpha=0.6)
            save_plot(output_folder, f"scatter_logpop_vs_idhm_{latest_year}.png")
        else:
            print("⚠️ Skipping LogPop vs IDHM scatter: No positive population data found.")


        # Plot 3.2: Boxplot of IDHM by CCAA
        ccaas_sorted = sorted(df_latest["CODAUTO"].dropna().unique())
        if ccaas_sorted:
            plt.figure(figsize=(12, 7))
            data_for_boxplot = [df_latest[df_latest["CODAUTO"] == c]["IDHM"].dropna() for c in ccaas_sorted]
            plt.boxplot(data_for_boxplot, labels=ccaas_sorted, showfliers=False) # Hide outliers for clarity
            plt.xlabel("CCAA (código)")
            plt.ylabel("IDHM")
            plt.title(f"Distribución de IDHM por CCAA ({latest_year})")
            plt.xticks(rotation=90, fontsize=8)
            plt.grid(axis='y', linestyle='--', alpha=0.7)
            save_plot(output_folder, f"boxplot_idhm_by_ccaa_{latest_year}.png")
        else:
            print("⚠️ Skipping IDHM by CCAA boxplot: No valid CCAA codes found.")


        # Plot 3.3: IDHM Trend: National vs Top 3 CCAA
        if not df.empty:
            mean_nacional = df.groupby("year")["IDHM"].mean().reset_index(name="Nacional")
            mean_ccaa = df.groupby(["year", "CODAUTO"])["IDHM"].mean().reset_index()
            # Identify top 3 CCAA by IDHM in the latest year
            top3_ccaas = mean_ccaa[mean_ccaa["year"] == latest_year].nlargest(3, "IDHM")["CODAUTO"].tolist()

            plt.figure(figsize=(10, 6))
            plt.plot(mean_nacional["year"], mean_nacional["Nacional"], label="Nacional", linewidth=2.5, marker='o')
            for cc in top3_ccaas:
                series = mean_ccaa[mean_ccaa["CODAUTO"] == cc]
                plt.plot(series["year"], series["IDHM"], label=f"CCAA {cc}", marker='^', linestyle='--')
            plt.xlabel("Año")
            plt.ylabel("IDHM medio")
            plt.title("Evolución del IDHM: nacional vs top 3 CCAA")
            plt.legend()
            plt.grid(True, linestyle='--', alpha=0.7)
            save_plot(output_folder, "trend_idhm_national_vs_top3.png")
        else:
            print("⚠️ Skipping trend plot: No overall data loaded.")

    else:
         print(f"⚠️ Skipping advanced plots: No data for year {latest_year} or missing required columns.")

    # === Plot Group 4: Multivariate and Advanced Plots ===
    if not df_latest.empty and all(c in df_latest.columns for c in ["I_ingresos", "I_educ", "I_salud", "population"]):
        print("\nGenerating multivariate plots...")
        df_latest = df_latest.copy()

        # Plot 4.1: Scatter Ingresos vs Educacion, color=Salud, size=Log(Pop)
        pop_pos = df_latest[df_latest["population"] > 0]
        if not pop_pos.empty:
            plt.figure(figsize=(10, 8))
            sizes = np.log10(pop_pos["population"] + 1) * 15 # Adjust multiplier for appropriate size
            sc = plt.scatter(
                pop_pos["I_ingresos"], pop_pos["I_educ"],
                c=pop_pos["I_salud"], cmap="viridis", # Use a perceptually uniform colormap
                s=sizes,
                alpha=0.6,
                edgecolors='grey', linewidth=0.5 # Add edgecolors for better visibility
            )
            plt.colorbar(sc, label="I_salud")
            plt.xlabel("I_ingresos")
            plt.ylabel("I_educ")
            plt.title(f"Ingresos vs Educación ({latest_year}) – color=Salud, tamaño=Log(Población)")
            plt.grid(True, linestyle=':', alpha=0.6)
            save_plot(output_folder, f"scatter_multivar_{latest_year}.png")
        else:
            print("⚠️ Skipping multivariate scatter: No positive population data found.")

        # Plot 4.2: KDE of IDHM by Population Quartiles
        try:
            df_latest["pop_quartile"] = pd.qcut(df_latest["population"], 4, labels=["Q1_Bajo", "Q2", "Q3", "Q4_Alto"])
            plt.figure(figsize=(9, 6))
            for q in df_latest["pop_quartile"].cat.categories:
                subset = df_latest[df_latest["pop_quartile"] == q]
                subset["IDHM"].plot(kind="kde", label=q, linewidth=2)
            plt.xlabel("IDHM")
            plt.title(f"Densidad de IDHM por cuartiles de población ({latest_year})")
            plt.legend(title="Cuartil población")
            plt.grid(axis='x', linestyle='--', alpha=0.7)
            save_plot(output_folder, f"kde_idhm_by_pop_quartile_{latest_year}.png")
        except ValueError:
            print("⚠️ Skipping KDE by population quartile: Not enough distinct population values for 4 quartiles.")
        except Exception as e:
            print(f"⚠️ Error generating KDE plot: {e}")


        # Plot 4.3: Correlation Evolution: Sub-indices vs IDHM
        if not df.empty and all(c in df.columns for c in ["I_ingresos", "I_salud", "I_educ", "IDHM"]):
            corrs = []
            years = sorted(df["year"].unique())
            for yr in years:
                subset = df[df["year"] == yr]
                # Calculate correlation only if data exists for the year
                if not subset.empty and len(subset) > 1: # Need at least 2 data points for correlation
                    # Ensure columns are numeric before calculating correlation
                    num_subset = subset[["I_ingresos", "I_salud", "I_educ", "IDHM"]].apply(pd.to_numeric, errors='coerce').dropna()
                    if len(num_subset) > 1:
                         corr = num_subset.corr().loc["IDHM", ["I_ingresos", "I_salud", "I_educ"]]
                         corr['year'] = yr
                         corrs.append(corr)
                    else:
                         print(f"⚠️ Insufficient non-NA data to calculate correlation for year {yr}")

            if corrs:
                corr_df = pd.DataFrame(corrs).set_index('year')
                plt.figure(figsize=(10, 6))
                for col in corr_df.columns:
                    plt.plot(corr_df.index, corr_df[col], marker='o', linestyle='-', label=col)
                plt.xlabel("Año")
                plt.ylabel("Correlación con IDHM")
                plt.title("Evolución de la correlación de cada sub-índice con IDHM")
                plt.legend()
                plt.ylim(-0.1, 1.1) # Set y-axis limits for correlation
                plt.grid(True, linestyle='--', alpha=0.7)
                save_plot(output_folder, "correlation_evolution_subindices_vs_idhm.png")
            else:
                print("⚠️ Skipping correlation evolution plot: No correlation data calculated.")
        else:
            print("⚠️ Skipping correlation evolution plot: Missing required columns in main dataframe.")

    else:
         print(f"⚠️ Skipping multivariate/advanced plots: No data for year {latest_year} or missing required columns.")

    print("\n--- Visualization Script Finished ---")

if __name__ == "__main__":
    # Check for matplotlib installation
    try:
        import matplotlib
    except ImportError:
        print("--------------------------------------------------------------------")
        print("ERROR: Library 'matplotlib' is needed for this script.")
        print("Please install it using: pip install matplotlib")
        print("--------------------------------------------------------------------")
        exit()
    main()