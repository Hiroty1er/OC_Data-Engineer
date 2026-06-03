# Migration de données CSV vers MongoDB avec Docker

Ce projet permet d’importer un fichier CSV (contenant des données de santé) dans une base de données MongoDB en utilisant un script Python.  
L’ensemble est conteneurisé avec Docker Compose, et un utilisateur MongoDB dédié (`migration`) avec des droits limités (lecture, écriture, mise à jour) est créé automatiquement.

## Fonctionnalités

- Lecture d’un fichier CSV (`healthcare_dataset.csv`) avec **pandas**.
- Nettoyage et transformation des données (suppression des doublons, conversion des dates, renommage des colonnes).
- Génération d’un identifiant unique (`_id`) via hash SHA256.
- Insertion ou mise à jour (upsert) en masse dans MongoDB avec `bulk_write`.
- Vérification de l’intégrité (comparaison du nombre de lignes entre le CSV et la base).
- Utilisation d’un **rôle personnalisé** MongoDB pour limiter les actions de l’utilisateur `migration` (uniquement `find`, `insert`, `update`).
- Orchestration via Docker Compose (MongoDB 8.0 + Python 3.12-slim).

## Prérequis

- Docker et Docker Compose installés.
- Un fichier `.env` à la racine du projet (voir la section **Configuration**).
- Le fichier CSV à importer doit s’appeler `healthcare_dataset.csv` (structure attendue décrite plus bas).

## Structure des fichiers

```
.
├── docker-compose.yml
├── Dockerfiles/
│   ├── mongo.dockerfile          # Construction de l'image mongodb copie le fichier init-mongo.js dans le dossier 
│   └── python.dockerfile
├── init-mongo.js                 # Script JS d’initialisation de MongoDB (création rôle/utilisateur)
├── migration.py                  # Script Python de migration
├── .env                          # Variables d’environnement (à créer)
└── healthcare_dataset.csv        # Données source (à placer)
```

## Configuration

Créez un fichier `.env` à la racine avec les variables suivantes :

```env
# MongoDB root
ROOT_PASS=<root_example_password>

# Utilisateur migration
MIGRATION_PASS=<migration_example_password>

# Nom de la base de données cible
DB_NAME=migration_db

# Répertoire de travail dans le conteneur Python
PYTHON_WORKING_DIR=<nom_du_dossier>
```

> Le script `init-mongo.js` utilise `DB_NAME`, `MG_USERNAME` (fixé à `migration`) et `MG_PASSWORD` pour créer l’utilisateur et le rôle.

## Installation et exécution

1. **Cloner ou copier les fichiers** dans un dossier.
2. **Placer le fichier CSV** :  
   Copiez `healthcare_dataset.csv` dans le même dossier que `docker-compose.yml`.
3. **Créer le fichier `.env`** avec vos mots de passe.
4. **Démarrer les conteneurs** :
   ```bash
   docker-compose up -d
   ```
   - Le conteneur MongoDB s’initialise et crée l’utilisateur `migration`.
   - Le conteneur Python reste en vie (`tail -f /dev/null`).
5. **Lancer le script de migration** :
   ```bash
   docker compose exec python_3.12-slim python3 migration.py
   ```
6. **Vérifier les logs** :
   ```bash
   docker logs mongodb_8_0       # pour voir l’initialisation MongoDB
   docker  migration.log             # fichier de log généré par le script Python
   ```

## Structure attendue du fichier CSV

Le script `migration.py` s’attend aux colonnes suivantes (nom d’origine / nom après transformation) :

| Colonne d’origine        | Colonne MongoDB | Type          |
|--------------------------|----------------|---------------|
| Name                     | name           | string        |
| Age                      | age            | int           |
| Gender                   | gender         | string        |
| Blood Type               | blood_type     | string        |
| Medical Condition        | medical_condition | string     |
| Date of Admission        | date_of_admission | datetime   |
| Doctor                   | doctor         | string        |
| Hospital                 | hospital       | string        |
| Insurance Provider       | insurance_provider | string     |
| Billing Amount           | billing_amount | float         |
| Room Number              | room_number    | int           |
| Admission Type           | admission_type | string        |
| Discharge Date           | discharge_date | datetime      |
| Medication               | medication     | string        |
| Test Results             | test_results   | string        |
 
Le script supprime les doublons
Format la colonne `Name` (`.strip().title()`), pour les noms soit écris avec une majuscule sur la première lettre.

## Détails techniques

### Initialisation MongoDB

- Le script `init-mongo.js` est exécuté automatiquement au premier démarrage du conteneur MongoDB.
- Il crée un **rôle personnalisé** nommé d’après la variable `MG_USERNAME` (ici `migration`) avec les actions autorisées : `find`, `insert`, `update`.
- Il crée ensuite un utilisateur `migration` avec ce rôle sur la base définie par `DB_NAME`.
- Aucun droit de suppression, de création d’index ou de drop de collection n’est accordé.

### Script Python

- Connexion à MongoDB avec les variables d’environnement (`MG_HOST`, `MG_PORT`, `MG_USERNAME`, `MG_PASSWORD`, `DB_NAME`).
- Lecture du CSV avec `pandas` en forçant les types.
- Génération de l’`_id` par hash SHA256 de la ligne entière convertie en chaîne.
- Utilisation de `bulk_write` avec des opérations `UpdateOne` (upsert) pour insérer/mettre à jour efficacement.
- Comparaison du nombre de lignes entre le DataFrame et la collection après insertion (`contrôle_integrite`).
- Les logs sont écrits dans le répertoire d'éxecution du script migration.py dans le fichier `migration.log` et affichés sur la console.

### Workaround pour MongoDB 8.0

Dans `docker-compose.yml`, la variable `GLIBC_TUNABLES=glibc.cpu.hwcaps=-SHSTK` est nécessaire pour contourner un problème de compatibilité avec certaines versions de MongoDB 8.0.

## Commandes utiles

| Action | Commande |
|--------|----------|
| Démarrer les services | `docker-compose up -d` |
| Arrêter les services | `docker-compose down` |
| Voir les logs Python | `docker logs py3.12-pymongo-pandas` |
| Exécuter une commande dans le conteneur Python | `docker exec -it py3.12-pymongo-pandas bash` |
| Réinitialiser les volumes (effacer les données MongoDB) | `docker-compose down -v` |

## Personnalisation

- **Autre fichier CSV** : modifiez le nom du fichier dans `migration.py` (ligne `migrate_csv_to_mongodb(f"/{WORK_DIR}/healthcare_dataset.csv")`).
- **Autres droits MongoDB** : éditez le tableau `actions` dans `init-mongo.js` (par exemple ajouter `"delete"`).
- **Planification** : vous pouvez ajouter un `cron` dans le conteneur Python ou utiliser un orchestrateur externe.

## Dépannage

- **Erreur de connexion MongoDB** : vérifiez que le conteneur `mongodb_8_0` est bien démarré (`docker ps`). Attendez quelques secondes que l’initialisation soit terminée.
- **Role/user already exists** : ce n’est pas bloquant, le script JS ignore la création si l’entité existe déjà.
- **Pandas type conversion error** : vérifiez que le CSV ne contient pas de valeurs vides inattendues (le script utilise `keep_default_na=False` et `na_values=[]` pour éviter les `NaN`).
- **GLIBC_TUNABLES** : Obligatoire pour MongoDB 8.0
