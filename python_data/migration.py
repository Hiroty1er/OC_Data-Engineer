#!/usr/bin/env python3
import os
import pandas as pd
import numpy as np
from datetime import datetime
from pymongo import MongoClient, errors

# Récupère la variable d'environnement donné par docker-compose.yml
MONGO_URI = os.getenv("MONGO_URI")
DATABASE_NAME = os.getenv("DATABASE_NAME")
COLLECTION_NAME = "healthcare_records"


def parse_date(date_str):
    """Convertit une chaîne YYYY-MM-DD en objet datetime."""
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        print(f"Format de date invalide : {date_str}")
        return None


def migrate_csv_to_mongodb(csv_file_path):
    """Lit le CSV avec pandas, nettoie les données et les insère dans MongoDB."""
    client = MongoClient(MONGO_URI)
    db = client[DATABASE_NAME]
    collection = db[COLLECTION_NAME]

    try:
        # Lecture du CSV en forçant le type str pour conserver les valeurs vides
        df = pd.read_csv(csv_file_path, dtype=str, keep_default_na=False, na_values=[])

        # Nettoyage des chaînes de caractères (strip)
        string_cols = [
            "Name", "Gender", "Blood Type", "Medical Condition",
            "Doctor", "Hospital", "Insurance Provider",
            "Admission Type", "Medication", "Test Results"
        ]
        for colonne in string_cols:
            df[colonne] = df[colonne].str.strip()

        # Mise en majuscule des noms des patients
        df["Name"] = df["Name"].str.upper()

        # Conversion des champs numériques (vides ou invalides → NaN)
        df["Age"] = pd.to_numeric(df["Age"], errors="coerce")
        df["Billing Amount"] = pd.to_numeric(df["Billing Amount"], errors="coerce")
        df["Room Number"] = pd.to_numeric(df["Room Number"], errors="coerce")

        # Parsing des dates (format jj/mm/aaaa par défaut)
        df["Date of Admission"] = pd.to_datetime(
            df["Date of Admission"], dayfirst=False, errors="coerce"
        )

        df["Discharge Date"] = pd.to_datetime(
            df["Discharge Date"], dayfirst=False, errors="coerce"
        )

        # Renommage des colonnes pour correspondre aux clés MongoDB
        df.rename(
            columns={
                "Name": "name",
                "Age": "age",
                "Gender": "gender",
                "Blood Type": "blood_type",
                "Medical Condition": "medical_condition",
                "Date of Admission": "date_of_admission",
                "Doctor": "doctor",
                "Hospital": "hospital",
                "Insurance Provider": "insurance_provider",
                "Billing Amount": "billing_amount",
                "Room Number": "room_number",
                "Admission Type": "admission_type",
                "Discharge Date": "discharge_date",
                "Medication": "medication",
                "Test Results": "test_results",
            },
            inplace=True,
        )
        
        # Conversion en liste de dictionnaires et nettoyage final
        records = df.to_dict(orient="records")

        # Insertion en bloc dans MongoDB
        if records:
            result = collection.insert_many(records)
            print(f"✅ {len(result.inserted_ids)} documents insérés dans la collection '{COLLECTION_NAME}'.")
        else:
            print("Aucune donnée à insérer.")

        # Contrôle d'intégrité simple
        # Vérifie le nombre de ligne présente en base avec ceux présent dans le csv.
        
        nb_ligne_csv = len(df)
        nb_ligne_db = collection.count_documents({})

        if nb_ligne_csv == nb_ligne_db:
            print(f"✅ Nombe de ligne identique entre le csv et la base de donnée")
        else:
            diff = nb_ligne_csv - nb_ligne_db
            if diff > 0:
                print(f"❌ il manque '{diff}' lignes")
            elif diff < 0:
                print(f"❌ il y a '{diff}' lignes en trop")

    except FileNotFoundError:
        print(f"❌ Fichier introuvable : {csv_file_path}")
    except errors.PyMongoError as e:
        print(f"❌ Erreur MongoDB : {e}")
    except Exception as e:
        print(f"❌ Erreur générale : {e}")
    finally:
        client.close()


if __name__ == "__main__":
    csv_file = "/scripts/healthcare_dataset.csv"  # À adapter si le nom diffère
    migrate_csv_to_mongodb(csv_file)

# Faire des tests (pytest) après chaque étape de la migration.
# Modifier le formatage des données pour une éxécution avec pandas.