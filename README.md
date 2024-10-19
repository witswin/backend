# Witswin Project

## Overview

Witswin is a Django-based web application designed for hosting quizzes and competitions. The project aims to provide a platform for users to participate in quizzes, compete with others, and win prizes.

## Features

- [x] User registration and authentication
- [x] Quiz implementation and score calculation
- [x] Privy authentication
- [x] Websocket implementation

- [ ] Dashboard for managing quizzes
- [ ] Quiz entry fees
- [ ] Random question decision
- [ ] Telegram mini app implementation
- [ ] Spectators in quiz
- [ ] Periodic quizzes
- [ ] Random questions from quiz bank
- [ ] Stats Hint
- [ ] Extra time Hint
- [ ] Veteran Hint

## Contributing

---

We welcome contributions from developers, designers, and anyone interested in improving the project. Here are ways to contribute:

### 1. Reporting Issues

- If you find a bug or issue, create a new issue on the GitHub issue tracker.
- Provide a clear description of the issue, steps to reproduce, and any relevant screenshots or logs.

### 2. Submitting Pull Requests

- Fork the repository and create a new branch for your feature or bug fix.
- Write clear and concise commit messages.
- Submit a pull request to the main repository.
- Ensure your code follows the project's coding standards and guidelines.

## Getting Started

## [![Open in Gitpod](https://gitpod.io/button/open-in-gitpod.svg)](https://gitpod.io/#https://github.com/witswin/backend)

---

To get started with the project, follow these steps:

### Create ENV

```env
POSTGRES_DB="wits"
POSTGRES_USER="postgres"
POSTGRES_PASSWORD="postgres"
FIELD_KEY="SECRET"
SECRET_KEY="django-insecure-!=_mi0j#rhk7c9p-0wg-3me6y&fk\$+fahz6fh)k1n#&@s(9vf5"
DEBUG="True"
SENTRY_DSN="DEBUG-DSN"


OP_MAINNET_RPC_URL="https://mainnet.optimism.io"


IMAGE_DELIVERY_URL=""
CLOUDFLARE_API_TOKEN=""
CLOUDFLARE_ACCOUNT_ID=""
CLOUDFLARE_ACCOUNT_HASH=""


PRIVY_APP_ID=""
PRIVY_APP_SECRET=""

PRIVY_JWKS_URL=""
```

<!-- ### Create base network

```
docker network create base
``` -->

### Launch docker instance:

```
docker compose up
```
