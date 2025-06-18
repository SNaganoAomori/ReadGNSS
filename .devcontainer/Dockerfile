# Python - DevContiner公式イメージ
# * GitHub | devcontainer/python : https://github.com/devcontainers/images/tree/main/src/python
FROM mcr.microsoft.com/devcontainers/python:3.12

# Git Subtree に必要な依存を含めて追加
RUN apt-get update \
    && export DEBIAN_FRONTEND=noninteractive \
    && apt-get upgrade -y \
    && apt-get install -y git curl make ca-certificates \
    && git clone https://github.com/git/git.git /tmp/git-src \
    && cp /tmp/git-src/contrib/subtree/git-subtree.sh /usr/local/bin/git-subtree \
    && chmod +x /usr/local/bin/git-subtree \
    && rm -rf /tmp/git-src \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt