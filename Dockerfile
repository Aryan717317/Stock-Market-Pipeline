FROM apache/airflow:3.3.1-python3.12
COPY --chown=airflow:root requirements*.txt /tmp/
RUN pip install --no-cache-dir "apache-airflow==3.3.1" -r /tmp/requirements-dev.txt \
    --constraint https://raw.githubusercontent.com/apache/airflow/constraints-3.3.1/constraints-3.12.txt \
    && pip check
COPY --chown=airflow:root . /opt/airflow/project
ENV PYTHONPATH=/opt/airflow/project \
    AIRFLOW__CORE__DAGS_FOLDER=/opt/airflow/project/dags
RUN mkdir -p /opt/airflow/auth /opt/airflow/logs
WORKDIR /opt/airflow/project
