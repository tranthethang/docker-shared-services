# Dozzle authentication (simple / users.yml)

Dozzle uses `--auth-provider=simple` and reads users from `dozzle/data/users.yml`.

## Login

- Username: `admin`
- Password: `DSS_SHARED_PASSWORD` from the root `.env` after `make setup`

Dozzle stores a **bcrypt hash** in `users.yml`.

## Create `dozzle/data/users.yml` manually

Load the shared password from the root `.env`, then generate the users file:

```bash
DSS_SHARED_PASSWORD=$(python3 -c "import sys; sys.path.insert(0, 'bin'); from utils import read_env_value; print(read_env_value('.env', 'DSS_SHARED_PASSWORD'))")
docker run --rm -i amir20/dozzle generate admin \
  --password "$DSS_SHARED_PASSWORD" \
  --email admin@example.com \
  --name "Admin" > ./dozzle/data/users.yml
```

`make setup` creates `dozzle/data/users.yml` if it is missing.

## Run from the repository root

`make up` runs Docker Compose from the repository root. The volume uses `${PWD}/dozzle/data:/data` so it mounts the Dozzle data directory.

To recreate an existing container after changing its mount:

```bash
make up service=dozzle
# Or:
docker compose -f docker-compose.shared.yml -f dozzle/docker-compose.yml up -d --force-recreate
```
