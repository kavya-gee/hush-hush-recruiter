FROM ubuntu:22.04

# Avoid prompts from apt
ENV DEBIAN_FRONTEND=noninteractive

# Set timezone to prevent interactive prompts
RUN ln -fs /usr/share/zoneinfo/UTC /etc/localtime

RUN apt-get update && apt-get install -y \
    python3 python3-pip \
    nodejs npm \
    postgresql postgresql-client \
    sudo curl wget git \
    lsb-release \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user to run code
RUN useradd -m runner && \
    echo "runner ALL=(ALL) NOPASSWD: ALL" > /etc/sudoers.d/runner

# Set up Python environment
COPY requirements-docker.txt /tmp/
RUN pip3 install --no-cache-dir -r /tmp/requirements-docker.txt

# Set up Node.js environment
COPY package.json /tmp/
RUN cd /tmp && npm install

# Set up PostgreSQL
USER postgres
RUN /etc/init.d/postgresql start && \
    psql --command "CREATE USER evaluator WITH PASSWORD 'secure_password';" && \
    createdb -O evaluator evaluation_db && \
    echo "host all evaluator 0.0.0.0/0 md5" >> /etc/postgresql/14/main/pg_hba.conf && \
    echo "listen_addresses='*'" >> /etc/postgresql/14/main/postgresql.conf
USER root

COPY evaluators/ /evaluators/
RUN chmod +x /evaluators/*.py /evaluators/*.js

# Create and prepare workspace directory
RUN mkdir -p /workspace && chown -R runner:runner /workspace
WORKDIR /workspace

# Copy the entrypoint script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Switch to the non-root user
USER runner

ENTRYPOINT ["/entrypoint.sh"]