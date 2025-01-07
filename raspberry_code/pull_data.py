# -*- coding: utf-8 -*-

import time
import csv
import os
import subprocess
from datetime import datetime

# -------------------------------------------------------------------
# Paramètres
# -------------------------------------------------------------------
INTERVAL_MINUTES = 5
CSV_SOURCE_FILE = "sensor_data.csv"
LAST_VALUE_FILE = "last_value_sent.txt"
LOCAL_REPO_PATH = "Sawcrate0.github.io"
DATA_FOLDER = "data"
DEFAULT_START_TS = "2025-01-06 00:00:00"

# -------------------------------------------------------------------
# Programme principal (sans if __name__ == "__main__":)
# -------------------------------------------------------------------

print("[DEBUG] Démarrage du script push_data.py.")

while True:
    print("\n=== Nouvelle itération de la boucle ===")

    # 1) Charger le dernier timestamp envoyé
    try:
        with open(LAST_VALUE_FILE, "r") as f:
            last_sent_str = f.read().strip()
            last_sent_ts = datetime.strptime(last_sent_str, "%Y-%m-%d %H:%M:%S")
        print(f"[DEBUG] On a récupéré last_sent_ts = {last_sent_ts}")
    except FileNotFoundError:
        print(f"[WARN] Fichier '{LAST_VALUE_FILE}' introuvable, on initialise à {DEFAULT_START_TS}")
        last_sent_ts = datetime.strptime(DEFAULT_START_TS, "%Y-%m-%d %H:%M:%S")
    except Exception as e:
        print(f"[ERROR] Problème avec '{LAST_VALUE_FILE}' : {e}")
        raise e

    # 2) Lire sensor_data.csv pour récupérer les lignes postérieures à last_sent_ts
    new_rows = []
    if os.path.exists(CSV_SOURCE_FILE):
        print(f"[DEBUG] Lecture du fichier '{CSV_SOURCE_FILE}'.")
        with open(CSV_SOURCE_FILE, "r", newline='') as csvfile:
            reader = csv.reader(csvfile)
            header = next(reader, None)  # Lecture de l'en-tête (on l'ignore ou on s'en sert si besoin)
            for row in reader:
                # row[2] = "YYYY-MM-DD HH:MM:SS"
                row_ts = datetime.strptime(row[2], "%Y-%m-%d %H:%M:%S")
                if row_ts > last_sent_ts:
                    new_rows.append(row)
        print(f"[DEBUG] Nombre de lignes nouvelles : {len(new_rows)}")
    else:
        print(f"[WARN] Le fichier '{CSV_SOURCE_FILE}' n'existe pas. Aucun envoi possible.")

    # 3) S'il y a des nouvelles lignes, on crée un CSV daté et on push
    if new_rows:
        now = datetime.now()
        csv_name = now.strftime("%Y_%m_%d_%Hh%M") + ".csv"

        # Création du dossier data/ si nécessaire
        full_data_path = os.path.join(LOCAL_REPO_PATH, DATA_FOLDER)
        if not os.path.exists(full_data_path):
            os.makedirs(full_data_path)
        
        full_csv_path = os.path.join(full_data_path, csv_name)

        # Écriture du nouveau CSV
        try:
            with open(full_csv_path, "w", newline='') as f_out:
                writer = csv.writer(f_out)
                writer.writerow(["Temperature (C)", "Humidity (%)", "Date and Time"])
                writer.writerows(new_rows)
            print(f"[DEBUG] Nouveau CSV créé : {full_csv_path}")
        except Exception as e:
            print(f"[ERROR] Échec lors de l'écriture du fichier CSV : {e}")
            raise e

        # Mise à jour de last_value_sent.txt avec le dernier timestamp qu’on a envoyé
        last_ts_in_batch = new_rows[-1][2]
        with open(LAST_VALUE_FILE, "w") as f_txt:
            f_txt.write(last_ts_in_batch)
        print(f"[DEBUG] Mise à jour de '{LAST_VALUE_FILE}' avec {last_ts_in_batch}")

        # 4) Git pull/add/commit/push
        print("[DEBUG] Passage des commandes Git.")
        try:
            os.chdir(LOCAL_REPO_PATH)

            # a) Récupérer les dernières modifs du remote
            subprocess.run(["git", "pull", "origin", "main"], check=True)

            # b) Ajouter le nouveau CSV
            subprocess.run(["git", "add", os.path.join(DATA_FOLDER, csv_name)], check=True)

            # c) Commit
            commit_message = f"Add new data file {csv_name}"
            subprocess.run(["git", "commit", "-m", commit_message], check=True)

            # d) Push
            subprocess.run(["git", "push", "origin", "main"], check=True)

            print(f"[OK] Fichier envoyé sur GitHub : {csv_name}")
        except subprocess.CalledProcessError as e:
            print(f"[ERROR] La commande Git a échoué : {e}")
        finally:
            os.chdir("..")

    else:
        print("[INFO] Aucune donnée nouvelle à pousser.")

    # 5) Attente avant la prochaine itération
    print(f"[DEBUG] Pause de {INTERVAL_MINUTES} minutes.")
    try:
        time.sleep(INTERVAL_MINUTES * 60)
    except KeyboardInterrupt:
        print("[DEBUG] Arrêt par l'utilisateur.")
        break
