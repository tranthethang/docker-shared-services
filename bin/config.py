SERVICES = [
    "act_runner", "adminer", "appsmith", "chromadb", "concourse", "dockge",
    "dozzle", "gitea", "jenkins", "kafka", "mailpit", "mariadb", "memcached",
    "minio", "mongodb", "monitoring", "mysql8", "n8n", "portainer", "postgres",
    "rabbitmq", "redis", "redisinsight", "sonarqube", "traefik"
]

ACTIONS = ["up", "down", "stop", "restart", "logs"]

VALIDATION_RULES = {
    "minio": ["MINIO_ROOT_PASSWORD"],
    "mongodb": ["PASSWORD"],
    "mysql8": ["PASSWORD"],
    "postgres": ["PASSWORD"],
    "rabbitmq": ["RABBITMQ_PASSWORD"],
}

SERVICE_INFO_VARS = {
    "appsmith": ["APPSMITH_PORT"],
    "chromadb": ["CHROMADB_PORT"],
    "dozzle": ["DOZZLE_PORT"],
    "gitea": ["GITEA_HTTP_PORT", "GITEA_SSH_PORT"],
    "mongodb": ["MONGO_PORT"],
    "monitoring": ["GRAFANA_PORT", "LOKI_PORT"],
    "mysql8": ["MYSQL_PORT", "MYSQL_DATABASE"],
    "n8n": ["N8N_PORT"],
    "postgres": ["POSTGRES_PORT", "POSTGRES_DB"],
    "redis": ["REDIS_PORT"],
    "sonarqube": ["SONARQUBE_PORT"],
}
