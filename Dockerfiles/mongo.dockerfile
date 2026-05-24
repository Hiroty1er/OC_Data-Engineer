FROM mongo:8.0
RUN mkdir /data/log && mongod --logpath /data/log