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

COPY requirements.txt .
RUN --mount=type=ssh pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# Applies pending migrations before every start - safe to run repeatedly,
# alembic no-ops if the schema is already current.
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
