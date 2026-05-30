FROM python:3.12-slim
ARG PYTHON_WORKING_DIR
RUN mkdir /${PYTHON_WORKING_DIR}

COPY ./requirement.txt /${PYTHON_WORKING_DIR}
COPY ./migration.py /${PYTHON_WORKING_DIR}
COPY ./healthcare_dataset.csv /${PYTHON_WORKING_DIR}

RUN pip install -r /${PYTHON_WORKING_DIR}/requirement.txt