import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score
import matplotlib.pyplot as plt
import os
import sys

def predict_household_sizes():
    """
    Trains a linear regression model for average household size per CCAA based on 2021-2025 data,
    predicts values for 2010-2020, saves predictions to CSV, generates plots, and reports R-squared.
    """
    base_dir = os.path.dirname(os.path.realpath(__file__))
    
    input_file = os.path.join(base_dir, "data_final/tamaño_medio_hogares_ccaa_completo.csv")
    output_pred_dir = os.path.join(base_dir, "datos_prediccion")
    output_plot_dir = os.path.join(output_pred_dir, "plots")

    os.makedirs(output_pred_dir, exist_ok=True)
    os.makedirs(output_plot_dir, exist_ok=True)

    try:
        df_complete = pd.read_csv(input_file, sep=',')
    except FileNotFoundError:
        print(f"Error: Input file not found at {input_file}", file=sys.stderr)
        return
    except Exception as e:
        print(f"Error reading input file {input_file}: {e}", file=sys.stderr)
        return

    df_complete['comunidad_code'] = df_complete['comunidad_code'].astype(float).astype(int).astype(str).str.zfill(2)
    df_complete['año'] = df_complete['año'].astype(int)
    df_complete.rename(columns={'total': 'avg_household_size', 'año': 'year', 'comunidad_code': 'ccaa_code'}, inplace=True)

    all_predictions_list = []
    model_stats_list = []
    
    years_to_predict = np.arange(2010, 2021).reshape(-1, 1) 

    for ccaa_code, group in df_complete.groupby('ccaa_code'):
        print(f"Processing CCAA: {ccaa_code}", file=sys.stderr)
        
        train_data = group[(group['year'] >= 2021) & (group['year'] <= 2025)].copy()
        train_data.sort_values('year', inplace=True)

        if len(train_data) < 2:
            print(f"Warning: Not enough data points for CCAA {ccaa_code} to train a model. Skipping.", file=sys.stderr)
            for _, row in train_data.iterrows():
                 all_predictions_list.append({
                    'ccaa_code': ccaa_code, 'year': row['year'],
                    'avg_household_size': row['avg_household_size'], 'is_predicted': False
                })
            continue

        X_train = train_data['year'].values.reshape(-1, 1)
        y_train = train_data['avg_household_size'].values

        model = LinearRegression()
        model.fit(X_train, y_train)
        
        y_train_pred = model.predict(X_train)
        r2 = r2_score(y_train, y_train_pred)
        slope = model.coef_[0]
        intercept = model.intercept_

        model_stats_list.append({
            'ccaa_code': ccaa_code, 'r_squared_2021_2025': r2,
            'slope': slope, 'intercept': intercept
        })
        print(f"  CCAA {ccaa_code} - Fit on 2021-2025: R-squared={r2:.4f}, Slope={slope:.4f}, Intercept={intercept:.4f}", file=sys.stderr)

        y_pred_past = model.predict(years_to_predict)
        
        for i, year_val in enumerate(years_to_predict.flatten()):
            all_predictions_list.append({
                'ccaa_code': ccaa_code, 'year': year_val,
                'avg_household_size': y_pred_past[i], 'is_predicted': True
            })
        
        for _, row in train_data.iterrows():
            all_predictions_list.append({
                'ccaa_code': ccaa_code, 'year': row['year'],
                'avg_household_size': row['avg_household_size'], 'is_predicted': False
            })

        plt.figure(figsize=(12, 7)) # Slightly larger for more info
        plt.scatter(X_train.flatten(), y_train, color='blue', label=f'Actual Data (2021-2025)\nR²={r2:.3f}')
        
        all_years_for_line = np.arange(2010, 2026).reshape(-1, 1)
        regression_line = model.predict(all_years_for_line)
        plt.plot(all_years_for_line.flatten(), regression_line, color='red', linestyle=':', 
                 label=f'Linear Trend (Slope: {slope:.4f})')
        
        plt.plot(years_to_predict.flatten(), y_pred_past, color='green', linestyle='--', marker='o', 
                 markersize=4, label='Predicted Extrapolation (2010-2020)')
        
        plt.title(f'Average Household Size - CCAA {ccaa_code}')
        plt.xlabel('Year')
        plt.ylabel('Average Household Size')
        plt.legend(loc='best')
        plt.grid(True)
        plot_file_path = os.path.join(output_plot_dir, f'household_size_ccaa_{ccaa_code}.png')
        try:
            plt.savefig(plot_file_path)
            print(f"  Plot saved to {plot_file_path}", file=sys.stderr)
        except Exception as e_plot:
            print(f"  Error saving plot for CCAA {ccaa_code}: {e_plot}", file=sys.stderr)
        plt.close()

    df_all_predictions = pd.DataFrame(all_predictions_list)
    output_csv_path = os.path.join(output_pred_dir, "predicted_household_sizes_by_ccaa.csv")
    try:
        df_all_predictions.sort_values(['ccaa_code', 'year'], inplace=True)
        df_all_predictions.to_csv(output_csv_path, index=False)
        print(f"All predictions saved to {output_csv_path}", file=sys.stderr)
    except Exception as e_csv:
        print(f"Error saving predictions CSV: {e_csv}", file=sys.stderr)

    df_model_stats = pd.DataFrame(model_stats_list)
    stats_csv_path = os.path.join(output_pred_dir, "prediction_model_stats_by_ccaa.csv")
    try:
        df_model_stats.to_csv(stats_csv_path, index=False)
        print(f"Model stats saved to {stats_csv_path}", file=sys.stderr)
    except Exception as e_stat_csv:
        print(f"Error saving model stats CSV: {e_stat_csv}", file=sys.stderr)


if __name__ == "__main__":
    predict_household_sizes()
