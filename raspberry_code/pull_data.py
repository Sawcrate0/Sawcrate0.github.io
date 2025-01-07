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
LIST_OF_CSV_FILE = "list_of_csv.txt"  # Fichier qui stocke la liste de tous les CSV
DEFAULT_START_TS = "2025-01-06 00:00:00"

print("[DEBUG] Démarrage du script pull_data.py.")

while True:
    print("\n=== Nouvelle itération de la boucle ===")

    # 0) Se mettre à jour dès le début (pull)
    print("[DEBUG] On se place dans le repo local et on fait un pull (avec rebase).")
    try:
        os.chdir(LOCAL_REPO_PATH)
        subprocess.run(["git", "pull", "origin", "main", "--rebase"], check=True)
        os.chdir("..")
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Le pull initial a échoué : {e}")
        os.chdir("..")
        # On arrête la boucle pour éviter de continuer dans un état divergent
        break

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
        break

    # 2) Lire sensor_data.csv pour récupérer les lignes postérieures
    new_rows = []
    if os.path.exists(CSV_SOURCE_FILE):
        print(f"[DEBUG] Lecture du fichier '{CSV_SOURCE_FILE}'.")
        with open(CSV_SOURCE_FILE, "r", newline='') as csvfile:
            reader = csv.reader(csvfile)
            header = next(reader, None)  # lecture de l'entête (si présent)
            for row in reader:
                # row[2] = "YYYY-MM-DD HH:MM:SS"
                row_ts = datetime.strptime(row[2], "%Y-%m-%d %H:%M:%S")
                if row_ts > last_sent_ts:
                    new_rows.append(row)
        print(f"[DEBUG] Nombre de lignes nouvelles : {len(new_rows)}")
    else:
        print(f"[WARN] Le fichier '{CSV_SOURCE_FILE}' n'existe pas. Aucun envoi possible.")

    # 3) Créer et pousser le nouveau CSV si on a des données
    if new_rows:
        now = datetime.now()
        csv_name = now.strftime("%Y_%m_%d_%Hh%M") + ".csv"

        full_data_path = os.path.join(LOCAL_REPO_PATH, DATA_FOLDER)
        if not os.path.exists(full_data_path):
            os.makedirs(full_data_path)
        
        full_csv_path = os.path.join(full_data_path, csv_name)

        try:
            with open(full_csv_path, "w", newline='') as f_out:
                writer = csv.writer(f_out)
                writer.writerow(["Temperature (C)", "Humidity (%)", "Date and Time"])
                writer.writerows(new_rows)
            print(f"[DEBUG] Nouveau CSV créé : {full_csv_path}")
        except Exception as e:
            print(f"[ERROR] Échec d'écriture du CSV : {e}")
            # Pas de push, on arrête la boucle
            break

        # Mettre à jour last_value_sent.txt
        last_ts_in_batch = new_rows[-1][2]
        with open(LAST_VALUE_FILE, "w") as f_txt:
            f_txt.write(last_ts_in_batch)
        print(f"[DEBUG] Mise à jour de '{LAST_VALUE_FILE}' avec {last_ts_in_batch}")

        # 3.b) Mettre à jour list_of_csv.txt (append)
        list_file_path = os.path.join(LOCAL_REPO_PATH, LIST_OF_CSV_FILE)
        try:
            with open(list_file_path, "a", encoding="utf-8") as lf:
                # On ajoute une ligne du type : data/2025_01_07_15h17.csv
                lf.write(f"{DATA_FOLDER}/{csv_name}\n")
            print(f"[DEBUG] Ajout dans '{LIST_OF_CSV_FILE}' : {DATA_FOLDER}/{csv_name}")
        except Exception as e:
            print(f"[ERROR] Impossible de mettre à jour '{LIST_OF_CSV_FILE}' : {e}")
            break

        # 4) Git add/commit/push
        print("[DEBUG] Git add/commit/push")
        try:
            os.chdir(LOCAL_REPO_PATH)
            # On ajoute le CSV + list_of_csv.txt
            subprocess.run(["git", "add", os.path.join(DATA_FOLDER, csv_name)], check=True)
            subprocess.run(["git", "add", LIST_OF_CSV_FILE], check=True)

            commit_message = f"Add new data file {csv_name}"
            subprocess.run(["git", "commit", "-m", commit_message], check=True)
            subprocess.run(["git", "push", "origin", "main"], check=True)
            print(f"[OK] Fichier envoyé sur GitHub : {csv_name}")
        except subprocess.CalledProcessError as e:
            print(f"[ERROR] La commande Git a échoué : {e}")
        finally:
            os.chdir("..")
    else:
        print("[INFO] Aucune donnée nouvelle à pousser.")

    # 5) Pause avant la prochaine boucle
    print(f"[DEBUG] Pause de {INTERVAL_MINUTES} minutes.")
    try:
        time.sleep(INTERVAL_MINUTES * 60)
    except KeyboardInterrupt:
        print("[DEBUG] Arrêt par l'utilisateur.")
        break
