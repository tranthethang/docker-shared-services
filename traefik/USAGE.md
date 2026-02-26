# How to Route External Containers via Traefik

To make your containers from other `docker-compose.yml` files accessible via Traefik with a custom domain (e.g., `sitexxx.localhost`), follow these steps:

## 1. Connect to the shared network
Your service must join the `dev_tools` network, which is used by Traefik.

## 2. Add Traefik Labels
You need to add specific labels to your service to tell Traefik how to route the traffic.

### Example Configuration
Add this to your external `docker-compose.yml`:

```yaml
services:
  my-api:
    image: your-api-image:latest
    networks:
      - dev_tools
    labels:
      - "traefik.enable=true"
      # Define the domain
      - "traefik.http.routers.my-api.rule=Host(`sitexxx.localhost`)"
      # (Optional) Specify the port if your container exposes more than one
      - "traefik.http.services.my-api.loadbalancer.server.port=8080"
      # (Optional) Set the entrypoint (web for HTTP, websecure for HTTPS)
      - "traefik.http.routers.my-api.entrypoints=web"

networks:
  dev_tools:
    external: true
    name: dev_tools
```

## Key Labels Explained
- **`traefik.enable=true`**: Tells Traefik to process this container.
- **`traefik.http.routers.<name>.rule`**: Defines the matching rule (Host, Path, etc.).
- **`traefik.http.services.<name>.loadbalancer.server.port`**: The internal port your app listens on inside the container.

## Troubleshooting
- Ensure the container is actually running and joined to the `dev_tools` network: `docker network inspect dev_tools`.
- Check Traefik Dashboard at [http://localhost:8080](http://localhost:8080) to see if your router appears.
