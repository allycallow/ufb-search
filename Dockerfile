FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /usr/src/app

RUN pip install --upgrade pip && \
    pip install pipenv

COPY Pipfile Pipfile.lock ./

RUN pipenv install --deploy --ignore-pipfile

COPY app/ ./app/

CMD ["pipenv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]