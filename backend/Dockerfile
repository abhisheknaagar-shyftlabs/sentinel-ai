FROM python:3.12-slim

WORKDIR /app

# git + openssh-client: requirements.txt pulls shyftlabs-continuum over
# git+ssh (a private repo, see .env.example's comments on Continuum) - the
# build needs SSH access to github.com, forwarded from the host via
# BuildKit (see the docker build --ssh flag in the deploy guide).
RUN apt-get update && apt-get install -y --no-install-recommends \
        git openssh-client \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -p -m 0700 /root/.ssh \
    && ssh-keyscan github.com >> /root/.ssh/known_hosts

# requirements.lock.txt (generated via `pip freeze` from a known-working
# local venv) is used instead of requirements.txt's loose >= ranges - a
# fresh container has no pip cache to shortcut resolution the way local dev
# does, and the private continuum dependency's own pins collide with those
# ranges badly enough that pip's resolver blows past its backtracking limit
# (ResolutionTooDeep) trying to satisfy them from scratch. Exact-pinned
# versions mean no resolution search is needed at all. Regenerate with:
#   ./.venv/bin/pip freeze > requirements.lock.txt
COPY requirements.lock.txt .
RUN --mount=type=ssh pip install --no-cache-dir -r requirements.lock.txt

COPY . .

EXPOSE 8000

# Applies pending migrations before every start - safe to run repeatedly,
# alembic no-ops if the schema is already current.
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
