FROM python:3.10-slim
# FROM python:3.10-alpine

########################################
# add a user so we're not running as root
########################################
RUN useradd useruser

RUN python -m pip install --quiet poetry

RUN apt-get update
RUN apt-get install -y git
RUN apt-get clean


RUN mkdir -p build/github_linter

WORKDIR /build
ADD github_linter /build/github_linter
COPY poetry.lock .
COPY README.md .
COPY LICENSE .
COPY pyproject.toml .

RUN mkdir -p /home/useruser/
RUN chown useruser /home/useruser -R
RUN chown useruser /build -R

WORKDIR /build/
USER useruser
RUN mkdir -p ~/.config/

RUN python -m pip install --upgrade pip
RUN poetry install --no-dev

ENTRYPOINT [ "poetry","run" ]
