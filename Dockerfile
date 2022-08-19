FROM python:3.10 as builder

RUN apt-get -y update && \
    apt-get -y upgrade && \
    pip install --upgrade pip && \
    pip install poetry

COPY ./pyproject.toml ./poetry.lock /build/
COPY ./code_run /build/code_run

WORKDIR /build/

RUN poetry install && \
    poetry config virtualenvs.create false && \
    poetry build -f wheel

FROM python:3.10-alpine

COPY --from=builder /build/dist/ /dist/
SHELL ["/bin/ash", "-c"]
WORKDIR /dist/
RUN pip install $(ls -1 | head -n 1)

WORKDIR /config/
