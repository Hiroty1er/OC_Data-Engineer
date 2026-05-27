#!/usr/bin/env python3
import os
import pandas as pd
import hashlib
from pymongo import MongoClient, errors

# Récupère la variable d'environnement donné par docker-compose.yml
MONGO_URI = os.getenv("MONGO_URI")
DATABASE_NAME = os.getenv("DATABASE_NAME")
COLLECTION_NAME = "healthcare_records"


def make_id(ligne):
    key = f"{ligne['name']}|{ligne['date_of_admission']}|{ligne['hospital']}|{ligne['blood_type']}"
    return hashlib.sha256(key.encode()).hexdigest()


def controle_integrite(nb_ligne_csv, nb_ligne_db):
    if nb_ligne_csv == nb_ligne_db:
        print(f"✅ Nombre de ligne identique entre le csv et la base de donnée")
    else:
        diff = nb_ligne_csv - nb_ligne_db
        if diff > 0:
            print(f"❌ il manque '{diff}' lignes")
        elif diff < 0:
            print(f"❌ il y a '{diff}' lignes en trop")


def insert_bd(records, collection):
    # Insertion en bloc dans MongoDB
    if records:
        result = collection.update_many(records)
        print(f"✅ {len(result.inserted_ids)} documents insérés dans la collection '{COLLECTION_NAME}'.")
    else:
        print("Aucune donnée à insérer, records vide")


def migrate_csv_to_mongodb(csv_file_path):

    """Lit le CSV avec pandas, nettoie les données et les insère dans MongoDB."""

    client = MongoClient(MONGO_URI)
    db = client[DATABASE_NAME]
    collection = db[COLLECTION_NAME]

    try:
        # Lecture du CSV en forçant le type str pour conserver les valeurs vides
        df = pd.read_csv(
                csv_file_path,
                dtype={                   # Formatage des données
                    "Age":                int,
                    "Gender":             str,
                    "Blood Type":         str,
                    "Medical Condition":  str,
                    "Doctor":             str,
                    "Hospital":           str,
                    "Insurance Provider": str,
                    "Billing Amount":     float,
                    "Room Number":        int,
                    "Admission Type":     str,
                    "Medication":         str,
                    "Test Results":       str,
                },
                skip_blank_lines=True,    # pas de lignes vides
                keep_default_na=False,    # Pour éviter les fausses valeur Null
                na_values=[],
                parse_dates=["Date of Admission", "Discharge Date"],  # Conversion des dates pour mettre l'année en premier
                dayfirst=False,
                converters={"Name": lambda x: x.strip().title()}  # Formatage des noms pour mettre la 1er lettre en MAJ
            )

        df.drop_duplicates()

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

        # Création de l'identifiant avec un SHA256 sur les champs ["Name", "blood_type", "date_of_admission", "hospital"]
        # Le but et de pouvoir retrouver les identifiants lors de la prochaine update.
        # On en profite pour ajouter la colonne "id_"
        df.insert(loc=0, column="id_", value=df.apply(make_id, axis=1))

        # Conversion en liste de dictionnaires pour coller avec le format Document de MongoDB
        # insertions de type upsert des dataframe en base de données
        insert_bd(df.to_dict(orient="records"), collection)

        # Vérifie le nombre de ligne présente en base avec ceux présent dans le csv.
        # Dans le cas où la synchronisation serait interompu côté serveur on aura des lignes manquantes.
        controle_integrite(len(df), collection.count_documents({}))

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

# Faire un merge into à la place d'un insert.
# Ajouter une gestion des logs '– mongod ­­logpath myLogFile'
# Prendre en compte le hashage des mots de passe pour se connecter à la base de données.

# Ajouter un utilisateur "migration" pour limiter les possibilité d'action du script.

# Lire la documentation MongoDB pour en comprendre ces avantages par rapport à SQL. (Fait)
# Commencer à regarder une mise ne prod vers AWS.