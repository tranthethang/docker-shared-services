SERVICES = [
    "act_runner", "adminer", "concourse", "dockge", "gitea", "jenkins",
    "mailpit", "mariadb", "memcached", "minio", "monitoring", "mongodb", "mysql8", "n8n",
    "portainer", "postgres", "rabbitmq", "redis", "redisinsight", "sonarqube", "traefik",
    "dozzle", "chromadb", "appsmith"
]

ACTIONS = ["up", "down", "stop", "restart", "logs"]

VALIDATION_RULES = {
    "postgres": ["PASSWORD"],
    "mysql8": ["PASSWORD"],
    "mongodb": ["PASSWORD"],
    "rabbitmq": ["RABBITMQ_PASSWORD"],
    "minio": ["MINIO_ROOT_PASSWORD"],
}

SERVICE_INFO_VARS = {
    "postgres": ["POSTGRES_PORT", "POSTGRES_DB"],
    "mysql8": ["MYSQL_PORT", "MYSQL_DATABASE"],
    "mongodb": ["MONGO_PORT"],
    "redis": ["REDIS_PORT"],
    "gitea": ["GITEA_HTTP_PORT", "GITEA_SSH_PORT"],
    "sonarqube": ["SONARQUBE_PORT"],
    "monitoring": ["GRAFANA_PORT", "LOKI_PORT"],
    "n8n": ["N8N_PORT"],
    "dozzle": ["DOZZLE_PORT"],
    "chromadb": ["CHROMADB_PORT"],
    "appsmith": ["APPSMITH_PORT"],
}
