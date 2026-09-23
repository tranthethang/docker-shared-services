# Garage (S3-compatible object storage)

Replacement for the retired MinIO service. [Garage](https://garagehq.deuxfleurs.fr/) is an
S3-compatible object store; deployed here in single-node mode (`replication_factor = 1`).

- Image: `dxflrs/garage:v2.4.1` (latest stable, pinned — never `:latest`)
- Ports: `3900` S3 API · `3901` RPC · `3902` static website hosting · `3903` admin API/metrics
- Traefik: `https://s3.garage.dss.localhost` (S3 API), `https://admin.garage.dss.localhost` (admin API)
- Config: directory mount `./config` → `/etc/garage` (`GARAGE_CONFIG_FILE=/etc/garage/garage.toml`)

> **No web UI.** Garage has no MinIO-style console. Opening
> `https://admin.garage.dss.localhost/` in a browser returns
> `Unknown API endpoint: GET /` — that host is a REST Admin API (Bearer token),
> not a dashboard. Manage the cluster with the CLI below.

## Setup

1. Copy the env file and fill in the secrets:

   ```bash
   cp .env.example .env
   sed -i '' "s/^GARAGE_RPC_SECRET=.*/GARAGE_RPC_SECRET=$(openssl rand -hex 32)/" .env
   sed -i '' "s/^GARAGE_ADMIN_TOKEN=.*/GARAGE_ADMIN_TOKEN=$(openssl rand -base64 32)/" .env
   ```

   (drop the `''` after `-i` if you're on GNU sed/Linux)

1. Start it:

   ```bash
   docker compose up -d
   ```

1. **Bootstrap the cluster layout.** Unlike MinIO, Garage does not accept any data until you
   assign and apply a layout for the node, even in single-node mode:

   ```bash
   docker exec garage /garage node id -q
   # prints: <hex>@garage:3901 — use ONLY the hex part (or a unique prefix) for assign
   docker exec garage /garage layout assign -z dc1 -c 1G <hex-node-id>
   docker exec garage /garage layout apply --version 1
   ```

   `layout assign` expects a hexadecimal node-id prefix (`garage status` shows the short form).
   Passing the full `id@host:port` string fails with `0 nodes match`.

1. Create an access key and a bucket, then grant access:

   ```bash
   docker exec garage /garage key create my-app-key
   docker exec garage /garage bucket create my-bucket
   docker exec garage /garage bucket allow --read --write --owner my-bucket --key my-app-key
   ```

   The `key create` output prints an S3-style `Key ID` / `Secret key` pair — use these with any
   S3 client (aws-cli, mc, SDKs) pointed at `https://s3.garage.dss.localhost` (region: `garage`).

## CLI cheat sheet

All admin work goes through `docker exec garage /garage ...` (Garage v2.4.1).
Equivalent helper: `./scripts/cli.sh <subcommand> …` (same argv after `/garage`).

> **Do not** bind-mount a single file to `/etc/garage.toml`. Under OrbStack that path is
> invisible inside the distroless image (`ENOENT` on healthcheck and `docker exec`), which is
> why older compose files left the container permanently `unhealthy`. This stack mounts
> `./config` → `/etc/garage` and sets `GARAGE_CONFIG_FILE=/etc/garage/garage.toml`.

### Bootstrap / layout

```bash
docker exec garage /garage node id -q          # <hex>@garage:3901
docker exec garage /garage status              # short ID is enough
docker exec garage /garage layout assign -z dc1 -c 1G <hex-node-id>
docker exec garage /garage layout apply --version 1
docker exec garage /garage layout show
```

### Status / health

```bash
docker exec garage /garage status
docker exec garage /garage health
docker exec garage /garage stats
docker compose ps   # healthcheck should be "healthy" after recreate
```

### Access keys

```bash
docker exec garage /garage key create my-app-key
docker exec garage /garage key list
docker exec garage /garage key info my-app-key
docker exec garage /garage key rename my-app-key new-name
docker exec garage /garage key delete my-app-key
```

### Buckets

```bash
docker exec garage /garage bucket create my-bucket
docker exec garage /garage bucket list
docker exec garage /garage bucket info my-bucket
docker exec garage /garage bucket delete my-bucket

# Grant key → bucket
docker exec garage /garage bucket allow \
  --read --write --owner my-bucket --key my-app-key

# Revoke key → bucket
docker exec garage /garage bucket deny \
  --read --write --owner my-bucket --key my-app-key

# Quotas (example: 10GB / 1000 objects)
docker exec garage /garage bucket set-quotas my-bucket --max-size 10G --max-objects 1000

# Static website hosting
docker exec garage /garage bucket website --allow my-bucket
```

### Create key + bucket (copy-paste)

```bash
docker exec garage /garage key create my-app-key
docker exec garage /garage bucket create my-bucket
docker exec garage /garage bucket allow --read --write --owner my-bucket --key my-app-key
```

For more subcommands: `docker exec garage /garage --help`,
`docker exec garage /garage layout --help`,
`docker exec garage /garage bucket --help`,
`docker exec garage /garage key --help`.

## Path-style addressing is mandatory

Garage does **not** support virtual-hosted-style bucket addressing
(`bucket.s3.garage.dss.localhost`) the way current AWS S3 does by default — it only speaks
legacy **path-style** (`s3.garage.dss.localhost/bucket`). This isn't optional here: our
`garage.toml` has no `root_domain` set for `[s3_api]` on purpose, and Traefik only routes the
single host `s3.garage.dss.localhost` (no wildcard subdomain/cert per bucket). So every client
must force path-style, or requests will fail to resolve the bucket.

- **aws-cli**

  ```bash
  aws --endpoint-url https://s3.garage.dss.localhost \
      --region garage \
      s3 ls s3://my-bucket
  ```

  (aws-cli already defaults to path-style when `--endpoint-url` is set; no extra flag needed.)

- **boto3 (Python)**

  ```python
  import boto3
  from botocore.config import Config

  s3 = boto3.client(
      "s3",
      endpoint_url="https://s3.garage.dss.localhost",
      region_name="garage",
      aws_access_key_id="...",
      aws_secret_access_key="...",
      config=Config(s3={"addressing_style": "path"}),
  )
  ```

- **AWS JS/Node SDK (v3)**

  ```js
  new S3Client({
    endpoint: "https://s3.garage.dss.localhost",
    region: "garage",
    forcePathStyle: true, // s3ForcePathStyle in SDK v2
  });
  ```

- **mc (MinIO client)**

  ```bash
  mc alias set garage https://s3.garage.dss.localhost ACCESS_KEY SECRET_KEY --api S3v4 --path on
  ```

- **rclone** (`rclone.conf`)

  ```ini
  [garage]
  type = s3
  provider = Other
  endpoint = https://s3.garage.dss.localhost
  region = garage
  force_path_style = true
  ```

- **s3cmd** (`.s3cfg`)

  ```ini
  host_base = s3.garage.dss.localhost
  host_bucket = s3.garage.dss.localhost
  use_https = True
  ```

  (setting `host_bucket` the same as `host_base`, instead of the usual `%(bucket)s.host_base`,
  is what keeps s3cmd on path-style)

Reference: [Garage Quick Start](https://garagehq.deuxfleurs.fr/documentation/quick-start/) ·
[Garage — configuring S3 clients](https://garagehq.deuxfleurs.fr/cookbook/clients.html).
