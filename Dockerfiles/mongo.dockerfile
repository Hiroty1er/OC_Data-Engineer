FROM mongo:8.0

# Permet de lancer le script d'initialisation du container pour créer la base de donnée et l'utilisateur dédié à la migration.
COPY ./init-mongo.js /docker-entrypoint-initdb.d/init-mongo.js