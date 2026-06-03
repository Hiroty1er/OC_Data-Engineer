FROM mongo:8.0
COPY ../init-mongo.js /docker-entrypoint-initdb.d/init-mongo.js