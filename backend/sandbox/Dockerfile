FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOME=/tmp

RUN groupadd --gid 10001 sandbox \
    && useradd --uid 10001 --gid 10001 --no-create-home --shell /usr/sbin/nologin sandbox

WORKDIR /sandbox

COPY requirements.txt /sandbox/requirements.txt
RUN python -m pip install --no-cache-dir --disable-pip-version-check -r /sandbox/requirements.txt

COPY worker.py /sandbox/worker.py

USER 10001:10001
ENTRYPOINT ["python", "/sandbox/worker.py"]
