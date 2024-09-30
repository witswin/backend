# Builder stage
FROM pypy:3.10 AS builder

# Install dependencies for Rust and Python build requirements
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    libssl-dev \
    pkg-config \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Rust and Cargo
RUN curl https://sh.rustup.rs -sSf | sh -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"
RUN rustc --version && cargo --version

# Set work directory
WORKDIR /usr/src/app

# Upgrade pip and install Python dependencies into a virtual environment
RUN pip install --upgrade pip
COPY ./requirements.txt .
RUN pip install -r requirements.txt


# Final stage (runtime)
FROM pypy:3.10

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set work directory
WORKDIR /usr/src/app

# Install GCC
RUN apt update && apt install -y gcc

# Copy installed Python packages from builder stage
COPY --from=builder /opt/pypy/lib/pypy3.10/ /opt/pypy/lib/pypy3.10/
COPY --from=builder /opt/pypy/lib/pypy3.10/ /opt/pypy/lib/python3.8/
# this depends on what you are installing
COPY --from=builder /usr/local/bin /usr/local/bin

# Link pypy3 to python
# RUN ln -s /usr/local/bin/pypy3 /usr/local/bin/python

# Copy project files
COPY ./src .
COPY ./start.sh .
COPY ./celery.sh .

# RUN pypy3 manage.py collectstatic --noinput



# FROM pypy:3.10


# RUN apt-get update && apt-get install -y \
#     curl \
#     build-essential \
#     libssl-dev \
#     pkg-config \
#     && rm -rf /var/lib/apt/lists/*

# RUN curl https://sh.rustup.rs -sSf | sh -s -- -y
# ENV PATH="/root/.cargo/bin:${PATH}"
# RUN rustc --version && cargo --version


# # Set environment variables
# ENV PYTHONDONTWRITEBYTECODE 1
# ENV PYTHONUNBUFFERED 1

# # Set work directory
# WORKDIR /usr/src/app

# RUN apt update && apt install gcc


# # RUN apt-get update && \
# #     apt-get install -y --no-install-recommends \
# #     build-essential \
# #     gcc \
# #     libpq-dev \
# #     libc-dev \
# #     netcat-traditional \
# #     && apt-get clean && \
# #     rm -rf /var/lib/apt/lists/*


# RUN pip install --upgrade pip
# COPY ./requirements.txt .
# RUN pip install -r requirements.txt

# RUN ln -s /usr/local/bin/pypy3 /usr/local/bin/python


# # Copy project
# COPY ./src .
# COPY ./start.sh .
# COPY ./celery.sh .


# # RUN pypy3 manage.py collectstatic --noinput
