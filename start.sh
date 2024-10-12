pypy3 manage.py migrate

pypy3 -m daphne -b 0.0.0.0 -p ${PORT:-5000} witswin.asgi:application