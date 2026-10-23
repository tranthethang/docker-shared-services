# libreoffice-writer

A headless LibreOffice Writer runtime with the UNO bridge, packaged as a plain Docker container. It contains **no application code**: your project connects to the UNO listener (or mounts its own code) to create, edit, and convert documents.

## What is inside

- `libreoffice-writer`, `python3`, `python3-uno` (Debian trixie)
- Fonts: DejaVu, Liberation, Noto (full Vietnamese glyph coverage)
- Vietnamese support by default: `LANG=C.UTF-8`, `libreoffice-l10n-vi`, `hunspell-vi` spell-check dictionary
- `tini` as PID 1; [entrypoint.sh](entrypoint.sh) runs `soffice --headless` with a UNO socket listener and restarts it if it exits
- Runs as non-root user `app` (uid 1000); working directory and volume: `/data`

## Start and stop

From the repository root (requires `make setup` once for networks and `.env`):

```bash
make up service=libreoffice-writer
make health service=libreoffice-writer
make logs service=libreoffice-writer
make down service=libreoffice-writer
```

The first `make up` builds the image. `make up` does not rebuild after a Dockerfile or entrypoint change; use the Compose command below with `--build`.

Or directly with Compose:

```bash
docker compose --project-directory libreoffice-writer \
  -f docker-compose.shared.yml -f libreoffice-writer/docker-compose.yml up -d --build
```

## Connection details

| From                               | Address                   |
| ---------------------------------- | ------------------------- |
| Another container on `backend_net` | `libreoffice-writer:2002` |
| Host machine                       | `127.0.0.1:2002`          |

The UNO protocol has **no authentication**. The host port is bound to `127.0.0.1` only; never publish it on a public interface.

## Configuration

Set in `libreoffice-writer/.env` (see [.env.example](.env.example)):

| Variable                             | Default | Description                |
| ------------------------------------ | ------- | -------------------------- |
| `LIBREOFFICE_WRITER_UNO_PORT`        | `2002`  | Host port (localhost only) |
| `LIBREOFFICE_WRITER_CPUS_LIMIT`      | `1`     | CPU limit                  |
| `LIBREOFFICE_WRITER_MEMORY_LIMIT`    | `1G`    | Memory limit               |
| `LIBREOFFICE_WRITER_CPUS_RESERVED`   | `0.1`   | CPU reservation            |
| `LIBREOFFICE_WRITER_MEMORY_RESERVED` | `256M`  | Memory reservation         |

Container environment (defaults set in the image): `UNO_HOST=0.0.0.0`, `UNO_PORT=2002`.

## Using it from Python

The container ships the UNO bindings for its system Python, so the simplest way to run a script is inside the container. Mount or copy your script and data under `/data`:

```bash
docker cp my_script.py libreoffice-writer:/data/my_script.py
docker exec libreoffice-writer python3 /data/my_script.py
```

Minimal example that connects to the running listener and opens a document:

```python
import uno
from com.sun.star.beans import PropertyValue

local = uno.getComponentContext()
resolver = local.ServiceManager.createInstanceWithContext(
    "com.sun.star.bridge.UnoUrlResolver", local
)
ctx = resolver.resolve(
    "uno:socket,host=127.0.0.1,port=2002;urp;StarOffice.ComponentContext"
)
desktop = ctx.ServiceManager.createInstanceWithContext(
    "com.sun.star.frame.Desktop", ctx
)

hidden = PropertyValue()
hidden.Name, hidden.Value = "Hidden", True
doc = desktop.loadComponentFromURL("file:///data/input.docx", "_blank", 0, (hidden,))
print(doc.Text.String[:200])
doc.close(True)
```

Inside the container use `host=127.0.0.1`. From another container use `host=libreoffice-writer`; that client needs the `uno` Python module (for example `python3-uno` in its own image, or build `FROM` this image).

## Building your own image on top

```dockerfile
FROM dss/libreoffice-writer:1.0.0
COPY app/ /srv/app/
```

Start the listener as usual, or run your code in the same container and connect to `127.0.0.1:2002`.

## Use it from another Compose project

An application in another Compose project can use this runtime instead of bundling LibreOffice itself. The app container joins `backend_net`, connects to `libreoffice-writer:2002`, and needs the `uno` Python module in its own image (`python3-uno` on Debian, or build `FROM dss/libreoffice-writer:1.0.0`).

UNO resolves file URLs on the LibreOffice side, so both containers must see the same files at the same path: mount the shared volume `libreoffice-writer-data` at `/data` in the app container as well.

```yaml
services:
  app:
    environment:
      UNO_HOST: libreoffice-writer
      UNO_PORT: "2002"
      DATA_DIR: /data
    volumes:
      - libreoffice-writer-data:/data
    networks:
      - backend_net

volumes:
  libreoffice-writer-data:
    external: true

networks:
  backend_net:
    external: true
```

## Files and data

`/data` is the named volume `libreoffice-writer-data`. Copy files in and out:

```bash
docker cp input.docx libreoffice-writer:/data/input.docx
docker cp libreoffice-writer:/data/output.docx ./output.docx
```

For a bind mount instead, add a `volumes:` entry to your own override file. Files must be readable and writable by uid 1000.

## Quick checks

Convert a file with the command line (uses a separate profile, independent of the listener):

```bash
docker exec libreoffice-writer soffice --headless \
  -env:UserInstallation=file:///tmp/lo_cli \
  --convert-to pdf --outdir /data /data/input.docx
```

Verify the listener answers:

```bash
docker exec libreoffice-writer python3 -c \
  "import socket; socket.create_connection(('127.0.0.1', 2002), 5).close(); print('ok')"
```

## Troubleshooting

- **Container unhealthy right after start:** LibreOffice needs a few seconds; the healthcheck allows a 40 s start period.
- **Connection refused from another container:** confirm it is on `backend_net` and uses `libreoffice-writer:2002`.
- **Out-of-memory kills:** raise `LIBREOFFICE_WRITER_MEMORY_LIMIT`; large documents need more than the 1G default.
- **Missing glyphs or wrong layout:** add the needed fonts package to the [Dockerfile](Dockerfile) and rebuild.
- **Changed the Dockerfile or entrypoint:** `make up` starts the existing image and does not rebuild. Run `docker compose --project-directory libreoffice-writer -f docker-compose.shared.yml -f libreoffice-writer/docker-compose.yml up -d --build` to rebuild and restart.
- **Stuck document:** `docker restart libreoffice-writer`.
