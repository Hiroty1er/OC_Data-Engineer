FROM mongo:8.0
COPY ./init-mongo /docker-entrypoint-initdb.d/init-mongo.js