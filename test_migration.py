# test_migration.py

import os
import logging
import pytest
from unittest.mock import Mock, patch, MagicMock
import pandas as pd
from pymongo import errors
from migration import make_id, controle_integrite, insert_bd, migrate_csv_to_mongodb


# -------------------------------------------------------------------
# Tests pour make_id
# -------------------------------------------------------------------
def test_make_id_consistency():
    ligne = {"name": "John", "age": 30}
    id1 = make_id(ligne)
    id2 = make_id(ligne)
    assert id1 == id2
    assert isinstance(id1, str)
    assert len(id1) == 64  # sha256 -> 64 chars hex


def test_make_id_different_input():
    ligne1 = {"name": "John", "age": 30}
    ligne2 = {"name": "Jane", "age": 30}
    assert make_id(ligne1) != make_id(ligne2)


# -------------------------------------------------------------------
# Tests pour controle_integrite (capture des logs)
# -------------------------------------------------------------------
def test_controle_integrite_ok(caplog):
    caplog.set_level(logging.INFO)  # ← ajout essentiel
    controle_integrite(100, 100)
    assert "✅ Nombre de lignes identique" in caplog.text


def test_controle_integrite_missing_lines(caplog):
    caplog.set_level(logging.WARNING)  # optionnel, mais cohérent
    controle_integrite(100, 95)
    assert "❌ Il manque 5 lignes en base" in caplog.text


def test_controle_integrite_extra_lines(caplog):
    caplog.set_level(logging.WARNING)
    controle_integrite(100, 110)
    assert "❌ Il y a 10 lignes en trop en base" in caplog.text


# -------------------------------------------------------------------
# Tests pour insert_bd (avec mock de collection)
# -------------------------------------------------------------------
def test_insert_bd_empty_collection(caplog):
    caplog.set_level(logging.INFO)  # ← ajout essentiel
    collection_mock = Mock()
    insert_bd([], collection_mock)
    assert "Aucune donnée à insérer" in caplog.text


def test_insert_bd_success():
    collection_mock = Mock()
    # Simule un retour de bulk_write avec des compteurs
    bulk_result = Mock()
    bulk_result.upserted_count = 5
    bulk_result.modified_count = 2
    collection_mock.bulk_write.return_value = bulk_result

    records = [{"_id": f"id_{i}", "data": i} for i in range(7)]
    insert_bd(records, collection_mock)

    collection_mock.bulk_write.assert_called_once()
    args, kwargs = collection_mock.bulk_write.call_args
    operations = args[0]
    assert len(operations) == 7
    # Vérifie que chaque opération est un UpdateOne avec upsert
    from pymongo import UpdateOne
    for op in operations:
        assert isinstance(op, UpdateOne)
        assert op._upsert is True


def test_insert_bd_bulk_write_error(caplog):
    collection_mock = Mock()
    error_details = {"writeErrors": [{"idx": 0}]}
    collection_mock.bulk_write.side_effect = errors.BulkWriteError(error_details)

    records = [{"_id": "id1"}]
    insert_bd(records, collection_mock)
    assert "Erreur lors du bulk_write" in caplog.text


# -------------------------------------------------------------------
# Tests pour migrate_csv_to_mongodb (avec mocks de pandas, pymongo, env)
# -------------------------------------------------------------------
@pytest.fixture
def mock_env():
    """Simule les variables d'environnement nécessaires."""
    env_vars = {
        "DB_NAME": "test_db",
        "MG_HOST": "localhost",
        "MG_PORT": "27017",
        "MG_USERNAME": "user",
        "MG_PASSWORD": "pass",
        "WORK_DIR": "/fake"
    }
    with patch.dict(os.environ, env_vars):
        yield

@pytest.fixture
def mock_mongo_client(mock_env):
    """Mock MongoClient et le retour de la collection."""
    with patch("migration.MongoClient") as mock_client_class:
        mock_client = MagicMock()
        mock_db = MagicMock()
        mock_collection = MagicMock()
        mock_client.__getitem__.return_value = mock_db
        mock_db.__getitem__.return_value = mock_collection
        mock_client_class.return_value = mock_client
        yield mock_collection


def test_migrate_csv_success(mock_mongo_client, tmp_path):
    """Test complet avec un petit CSV généré à la volée."""
    # Créer un fichier CSV temporaire
    csv_data = pd.DataFrame({
        "Name": ["  john doe ", "JANE SMITH"],
        "Age": [45, 32],
        "Gender": ["M", "F"],
        "Blood Type": ["A+", "O-"],
        "Medical Condition": ["Hypertension", "Diabetes"],
        "Doctor": ["Dr A", "Dr B"],
        "Hospital": ["Hospital X", "Hospital Y"],
        "Insurance Provider": ["Ins A", "Ins B"],
        "Billing Amount": [1234.5, 5678.9],
        "Room Number": [101, 202],
        "Admission Type": ["Emergency", "Elective"],
        "Discharge Date": ["01/02/2023", "15/03/2023"],
        "Medication": ["MedX", "MedY"],
        "Test Results": ["Normal", "Abnormal"],
        "Date of Admission": ["31/01/2023", "10/03/2023"]
    })
    csv_path = tmp_path / "healthcare_dataset.csv"
    csv_data.to_csv(csv_path, index=False)

    # Simuler un compteur de documents dans la collection
    mock_mongo_client.count_documents.return_value = 2

    # Appeler la fonction (le chemin doit correspondre à /WORK_DIR/... mais on override)
    # Note : la fonction utilise f"/{WORK_DIR}/healthcare_dataset.csv", il faut donc adapter
    # Dans le test, on peut patcher le chemin ou changer le WORK_DIR temporairement
    with patch.dict(os.environ, {"WORK_DIR": str(tmp_path)}):
        migrate_csv_to_mongodb(f"{tmp_path}/healthcare_dataset.csv")

    # Vérifications
    mock_mongo_client.bulk_write.assert_called_once()
    # On peut aussi vérifier que les _id ont bien été ajoutés et que la transformation a eu lieu
    args, _ = mock_mongo_client.bulk_write.call_args
    operations = args[0]
    assert len(operations) == 2
    # Vérifier que chaque op contient un _id (sha256 de la ligne entière)
    for op in operations:
        doc = op._doc['$set']
        assert "_id" in doc
        assert "name" in doc
        assert doc["name"] in ["John Doe", "Jane Smith"]  # test du title() et strip
        assert "age" in doc
        assert "date_of_admission" in doc  # parse_dates a fonctionné


def test_migrate_csv_file_not_found(caplog, mock_mongo_client):
    """Test lorsque le fichier CSV est introuvable."""
    with patch.dict(os.environ, {"WORK_DIR": "/inexistant"}):
        migrate_csv_to_mongodb("/inexistant/healthcare_dataset.csv")
    assert "Fichier introuvable" in caplog.text
    mock_mongo_client.bulk_write.assert_not_called()


def test_migrate_csv_mongo_error(caplog, mock_mongo_client, tmp_path):
    """Test d'une erreur MongoDB lors de l'insertion."""
    # Créer un CSV minimal
    csv_path = tmp_path / "healthcare_dataset.csv"
    pd.DataFrame({
        "Name": ["Test"],
        "Age": [30],
        "Gender": ["M"],
        "Blood Type": ["A+"],
        "Medical Condition": ["Fever"],
        "Doctor": ["D"],
        "Hospital": ["H"],
        "Insurance Provider": ["I"],
        "Billing Amount": [100],
        "Room Number": [1],
        "Admission Type": ["Urgent"],
        "Discharge Date": ["01/01/2023"],
        "Medication": ["M"],
        "Test Results": ["Ok"],
        "Date of Admission": ["01/01/2023"]
    }).to_csv(csv_path, index=False)

    mock_mongo_client.bulk_write.side_effect = errors.PyMongoError("Fake connection error")

    with patch.dict(os.environ, {"WORK_DIR": str(tmp_path)}):
        migrate_csv_to_mongodb(f"{tmp_path}/healthcare_dataset.csv")
    assert "Erreur MongoDB : Fake connection error" in caplog.text