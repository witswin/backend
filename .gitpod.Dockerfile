FROM gitpod/workspace-full

# Install Docker CLI if needed
USER root
RUN apt-get update && \
  apt-get install -y docker-compose

USER gitpod
