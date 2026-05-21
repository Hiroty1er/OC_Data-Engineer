FROM python:3.12-slim
RUN pip install pymongo pandas numpy
COPY migration.py ./python_data
COPY healthcare_dataset.csv ./python_data