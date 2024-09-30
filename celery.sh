#!/bin/sh

pypy3 -m celery -A witswin worker --beat --concurrency 1 -l INFO 