FROM python:3.13-slim

########################################
# add a user so we're not running as root
########################################
RUN useradd useruser

RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && apt-get autoremove -y \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*


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

ENTRYPOINT ["/home/useruser/.local/bin/github-linter-web"]