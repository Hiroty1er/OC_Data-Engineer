#!/usr/bin/env python3
import os
import logging
import hashlib
import pandas as pd
from pymongo import MongoClient, errors, UpdateOne

# Configuration des logs
LOG_FILE = "./migration.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)

MONGO_URI = os.getenv("MONGO_URI")
DATABASE_NAME = os.getenv("DATABASE_NAME")
COLLECTION_NAME = "healthcare_records"


def make_id(ligne):
    key = f"{ligne}"
    return hashlib.sha256(key.encode()).hexdigest()


def insert_bd(records, collection):
    if not records:
        logging.info("Aucune donnée à insérer, records vide")
        return

    # Créer un tableau d'opération à effectuer
    operations = [UpdateOne({"_id": record["_id"]}, {"$set": record}, upsert=True) for record in records]

    logging.info(f"Préparation de {len(operations)} opérations upsert")

    try:
        # Effectue les opérations
        result = collection.bulk_write(operations, ordered=False)
        logging.info(f"✅ Insérés : {result.upserted_count} | Mis à jour : {result.modified_count}")

    except errors.BulkWriteError as e:
        logging.error(f"Erreur lors du bulk_write : {e.details}")


def controle_integrite(nb_ligne_csv, nb_ligne_db):
    if nb_ligne_csv == nb_ligne_db:
        logging.info("✅ Nombre de lignes identique entre le DataFrame pandas et la base")
    else:
        diff = nb_ligne_csv - nb_ligne_db
        if diff > 0:
            logging.warning(f"❌ Il manque {diff} lignes en base")
        else:
            logging.warning(f"❌ Il y a {-diff} lignes en trop en base")


def migrate_csv_to_mongodb(csv_file_path):
    client = MongoClient(MONGO_URI)
    db = client[DATABASE_NAME]
    collection = db[COLLECTION_NAME]

    try:
        df = pd.read_csv(
            csv_file_path,
            dtype={
                "Age": int,
                "Gender": str,
                "Blood Type": str,
                "Medical Condition": str,
                "Doctor": str,
                "Hospital": str,
                "Insurance Provider": str,
                "Billing Amount": float,
                "Room Number": int,
                "Admission Type": str,
                "Medication": str,
                "Test Results": str,
            },
            skip_blank_lines=True,
            keep_default_na=False,
            na_values=[],
            parse_dates=["Date of Admission", "Discharge Date"],
            dayfirst=False,
            converters={"Name": lambda x: x.strip().title()}
        )

        df.rename(columns={
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
        }, inplace=True)

        df.drop_duplicates(inplace=True)  # enlève les doublons (et il y en a)

        # Ajoute la colonne _id et créer les identifiant SHA256 avec make_id
        df.insert(0, "_id", df.apply(make_id, axis=1))

        insert_bd(df.to_dict(orient="records"), collection)
        controle_integrite(len(df), collection.count_documents({}))

    except FileNotFoundError:
        logging.error(f"Fichier introuvable : {csv_file_path}")
    except errors.PyMongoError as e:
        logging.error(f"Erreur MongoDB : {e}")
    except Exception as e:
        logging.error(f"Erreur générale : {e}")
    finally:
        client.close()


if __name__ == "__main__":
    migrate_csv_to_mongodb("/scripts/healthcare_dataset.csv")


# Ajouter une gestion des logs '– mongod ­­logpath myLogFile'
# Prendre en compte le hashage des mots de passe pour se connecter à la base de données.

# Ajouter un utilisateur "migration" pour limiter les possibilité d'action du script.

# Lire la documentation MongoDB pour en comprendre ces avantages par rapport à SQL. (Fait)
# Commencer à regarder une mise en prod vers AWS.