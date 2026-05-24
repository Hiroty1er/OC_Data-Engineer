FROM python:3.12-slim
RUN pip install pymongo pandas && mkdir /scripts
COPY ./migration.py /scripts
COPY ./healthcare_dataset.csv /scripts