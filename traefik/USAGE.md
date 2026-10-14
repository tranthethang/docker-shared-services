# How to Route External Containers via Traefik

To make your containers from other `docker-compose.yml` files accessible via Traefik with a custom domain (e.g., `sitexxx.dss.localhost`), follow these steps:

## 1. Connect to the shared network

Your service must join the `traefik_proxy` network, which is used by Traefik.

## 2. Add Traefik Labels

You need to add specific labels to your service to tell Traefik how to route the traffic.

### Example Configuration

Add this to your external `docker-compose.yml`:

```yaml
services:
  my-api:
    image: your-api-image:latest
    networks:
      - traefik_proxy
      - backend_net
    labels:
      - "traefik.enable=true"
      - "traefik.docker.network=traefik_proxy"
      # Define the domain
      - "traefik.http.routers.my-api.rule=Host(`sitexxx.dss.localhost`)"
      # (Optional) Specify the port if your container exposes more than one
      - "traefik.http.services.my-api.loadbalancer.server.port=8080"
      - "traefik.http.routers.my-api.entrypoints=websecure"
      - "traefik.http.routers.my-api.tls=true"

networks:
  traefik_proxy:
    external: true
    name: traefik_proxy
  backend_net:
    external: true
```

## Key Labels Explained

- **`traefik.enable=true`**: Tells Traefik to process this container.
- **`traefik.http.routers.<name>.rule`**: Defines the matching rule (Host, Path, etc.).
- **`traefik.http.services.<name>.loadbalancer.server.port`**: The internal port your app listens on inside the container.

## Troubleshooting

- Ensure the container is actually running and joined to the `traefik_proxy` network: `docker network inspect traefik_proxy`.
- Check the Traefik dashboard at [https://traefik.dss.localhost/dashboard/](https://traefik.dss.localhost/dashboard/) to see if your router appears. Log in as `admin` with `DSS_SHARED_PASSWORD` from the root `.env`.
