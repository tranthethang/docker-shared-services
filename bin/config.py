SERVICES = [
    "act_runner", "adminer", "appsmith", "chromadb", "chromadb_admin", "concourse", "dockge",
    "dozzle", "gitea", "jenkins", "kafka", "mailpit", "mariadb", "memcached",
    "minio", "mongodb", "monitoring", "mysql8", "n8n", "otel", "pgvector", "pocketbase", "postgres", "portainer",
    "rabbitmq", "redis", "redisinsight", "sonarqube", "temporal", "traefik", "woodpecker"
]

ACTIONS = ["up", "down", "stop", "restart", "logs"]

VALIDATION_RULES = {
    "minio": ["MINIO_ROOT_PASSWORD"],
    "mongodb": ["PASSWORD"],
    "mysql8": ["PASSWORD"],
    "pgvector": ["PASSWORD"],
    "postgres": ["POSTGRES16_PASSWORD"],
    "rabbitmq": ["RABBITMQ_PASSWORD"],
}

SERVICE_INFO_VARS = {
    "appsmith": ["APPSMITH_PORT"],
    "chromadb": ["CHROMADB_PORT"],
    "chromadb_admin": ["CHROMADB_ADMIN_PORT"],
    "dozzle": ["DOZZLE_PORT"],
    "gitea": ["GITEA_HTTP_PORT", "GITEA_SSH_PORT"],
    "mongodb": ["MONGO_PORT"],
    "monitoring": ["GRAFANA_PORT", "LOKI_PORT"],
    "mysql8": ["MYSQL_PORT", "MYSQL_DATABASE"],
    "n8n": ["N8N_PORT"],
    "otel": ["OTEL_COLLECTOR_PORT_GRPC", "JAEGER_PORT", "PROMETHEUS_PORT"],
    "pocketbase": ["POCKETBASE_PORT"],
    "pgvector": ["POSTGRES_PORT", "POSTGRES_DB"],
    "postgres": ["POSTGRES16_PORT", "POSTGRES16_DB"],
    "redis": ["REDIS_PORT"],
    "sonarqube": ["SONARQUBE_PORT"],
    "temporal": ["TEMPORAL_UI_PORT", "TEMPORAL_GRPC_PORT"],
    "woodpecker": ["WOODPECKER_HTTP_PORT"],
}
