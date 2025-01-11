FROM python:3.12-slim

########################################
# add a user so we're not running as root
########################################
RUN useradd useruser

RUN apt-get update
RUN apt-get install -y git
RUN apt-get clean


RUN mkdir -p build/github_linter

WORKDIR /build
ADD github_linter /build/github_linter
COPY pyproject.toml .
COPY README.md .
COPY LICENSE .

RUN mkdir -p /home/useruser/
RUN chown useruser /home/useruser -R
RUN chown useruser /build -R

WORKDIR /build/
USER useruser
RUN mkdir -p ~/.config/

RUN pip install --no-cache-dir --disable-pip-version-check /build/
