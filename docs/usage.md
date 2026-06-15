# Commands & Operations Guide

> Detailed command references for managing services, performing cleanups, and development pro-tips.

---

## 🔧 Usage & Commands

### Makefile (Recommended)

```bash
make help           # Show all commands
make setup          # Setup environment files, networks, and certs
make cert           # Generate SSL certificates
make up             # Start services (interactive or specific)
make down           # Stop and remove services
make stop           # Stop services (keep containers)
make ps             # Show service status
make logs           # View logs
make remove-all     # Remove containers & volumes
make restart        # Restart services
```

### Docker Compose Direct

```bash
docker compose ps                    # View status
docker compose logs -f               # View logs
docker compose logs -f [service]     # Specific service
docker compose down                  # Stop all
docker compose down -v               # Stop and remove volumes
```

---

## 🗑️ Cleanup

### Stop services (keep data)

```bash
make down
```

### Stop and remove volumes (delete data)

```bash
make remove-all
```

### Deep cleanup

```bash
make remove-all
make prune
docker system prune -a --volumes
```

---

## 🎯 Pro Tips

1. **Use Makefile** - Easier than docker-compose commands.
2. **Keep backups** of important databases before major changes.
3. **Monitor resources** - Watch with `docker stats`.
4. **Use .env files** - Don't hardcode sensitive values.
5. **Check logs first** - Most issues are revealed in logs.
6. **Use container names** for inter-service communication.
7. **Always use healthchecks** for critical services.

---

## 🔗 Quick Links

- [« Back to Main README](../README.md)
- [Services & Access Reference](services.md)
- [Configuration & Networking Guide](configuration.md)
- [Troubleshooting & Support](troubleshooting.md)
