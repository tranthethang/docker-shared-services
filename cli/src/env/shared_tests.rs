use super::*;

fn tree(name: &str) -> std::path::PathBuf {
    let dir = std::env::temp_dir().join(format!("dss-shared-{name}-{}", std::process::id()));
    let _ = fs::remove_dir_all(&dir);
    fs::create_dir_all(&dir).unwrap();
    dir
}

fn write(root: &Path, rel: &str, text: &str) {
    let path = root.join(rel);
    fs::create_dir_all(path.parent().unwrap()).unwrap();
    fs::write(path, text).unwrap();
}

#[test]
fn legacy_password_is_rejected() {
    let root = tree("legacy");
    let result = fill_shared_password(&root, Some("Password102!"), false, true);
    assert!(result.is_err(), "the legacy password must never be applied");
}

#[test]
fn root_env_legacy_password_is_replaced_by_a_generated_one() {
    let root = tree("rootlegacy");
    write(&root, ".env", "DSS_SHARED_PASSWORD=Password102!\n");
    let p = resolve_password(&root, None, None).unwrap();
    assert_ne!(p, "Password102!");
    assert_eq!(p.len(), 32);
}

#[test]
fn weak_explicit_password_is_refused() {
    let root = tree("weak");
    assert!(resolve_password(&root, Some("weak"), None).is_err());
    assert!(resolve_password(&root, None, Some("alsoweak")).is_err());
}

#[test]
fn resolve_order_is_explicit_env_root() {
    let root = tree("order");
    write(&root, ".env", "DSS_SHARED_PASSWORD=Root-Env-Password-1\n");
    assert_eq!(
        resolve_password(&root, Some("Strong-Password-123"), Some("x")).unwrap(),
        "Strong-Password-123"
    );
    assert_eq!(
        resolve_password(&root, None, Some("From-Env-Password-1")).unwrap(),
        "From-Env-Password-1"
    );
    assert_eq!(
        resolve_password(&root, None, None).unwrap(),
        "Root-Env-Password-1"
    );
}

#[test]
fn shared_password_overwrites_placeholders_only() {
    let root = tree("apply");
    write(
        &root,
        ".env",
        "DSS_SHARED_PASSWORD=\nREDIS_PASSWORD=custom\nPOSTGRES16_PASSWORD=Password102!\n",
    );
    write(
        &root,
        "zitadel/.env",
        "ZITADEL_ADMIN_PASSWORD=\nZITADEL_CACHES_CONNECTORS_REDIS_URL=x\n",
    );
    let pw = fill_shared_password(&root, Some("Strong-Password-123"), false, false).unwrap();
    let root_env = root.join(".env");
    assert_eq!(read_value(&root_env, "DSS_SHARED_PASSWORD").unwrap(), pw);
    assert_eq!(read_value(&root_env, "POSTGRES16_PASSWORD").unwrap(), pw);
    assert_eq!(read_value(&root_env, "REDIS_PASSWORD").unwrap(), "custom");
    let z = root.join("zitadel/.env");
    assert_eq!(read_value(&z, "ZITADEL_ADMIN_PASSWORD").unwrap(), pw);
    assert_eq!(
        read_value(&z, "ZITADEL_CACHES_CONNECTORS_REDIS_URL").unwrap(),
        "x"
    );
}

#[test]
fn force_rewrites_custom_values_and_dry_run_writes_nothing() {
    let root = tree("force");
    write(&root, ".env", "REDIS_PASSWORD=custom\n");
    fill_shared_password(&root, Some("Strong-Password-123"), false, true).unwrap();
    assert_eq!(
        read_value(&root.join(".env"), "REDIS_PASSWORD").unwrap(),
        "custom"
    );
    fill_shared_password(&root, Some("Strong-Password-123"), true, false).unwrap();
    assert_eq!(
        read_value(&root.join(".env"), "REDIS_PASSWORD").unwrap(),
        "Strong-Password-123"
    );
}

#[test]
fn fill_secrets_generates_each_kind_and_keeps_set_values() {
    let root = tree("fill");
    write(
        &root,
        "garage/.env",
        "GARAGE_RPC_SECRET=\nGARAGE_ADMIN_TOKEN=keep\n",
    );
    write(&root, "zitadel/.env", "ZITADEL_MASTERKEY=\n");
    write(
        &root,
        "supabase/.env",
        "JWT_SECRET=\nANON_KEY=\nSERVICE_ROLE_KEY=\n",
    );
    write(&root, "bugsink/.env", "BUGSINK_SECRET_KEY=\n");
    let filled = fill_secrets(&root, Some("all")).unwrap();
    assert!(filled >= 2);
    let get = |s: &str, k: &str| read_value(&root.join(s).join(".env"), k).unwrap();
    assert_eq!(get("garage", "GARAGE_RPC_SECRET").len(), 64);
    assert_eq!(get("garage", "GARAGE_ADMIN_TOKEN"), "keep");
    assert_eq!(get("zitadel", "ZITADEL_MASTERKEY").len(), 32);
    assert_eq!(get("supabase", "ANON_KEY").split('.').count(), 3);
    assert!(!get("bugsink", "BUGSINK_SECRET_KEY").is_empty());
}

#[test]
fn dashboard_auth_needs_shared_password_and_escapes_lone_dollars() {
    let root = tree("dash");
    write(&root, ".env", "DSS_SHARED_PASSWORD=Password102!\n");
    write(&root, "traefik/.env", "TRAEFIK_DASHBOARD_AUTH=\n");
    assert!(fill_secrets(&root, Some("traefik")).is_err());
    write(&root, ".env", "DSS_SHARED_PASSWORD=Strong-Password-123\n");
    fill_secrets(&root, Some("traefik")).unwrap();
    assert!(
        read_value(&root.join("traefik/.env"), "TRAEFIK_DASHBOARD_AUTH")
            .unwrap()
            .starts_with("admin:$$2y$$")
    );
    assert_eq!(escape_dollars("a$b$$c"), "a$$b$$c");
}

#[test]
fn garage_ui_token_is_copied_from_garage() {
    let root = tree("sync");
    write(&root, "garage/.env", "GARAGE_ADMIN_TOKEN=tok\n");
    write(&root, "garage_ui/.env", "GARAGE_ADMIN_TOKEN=\n");
    sync_garage_ui_token(&root);
    assert_eq!(
        read_value(&root.join("garage_ui/.env"), "GARAGE_ADMIN_TOKEN").unwrap(),
        "tok"
    );
}
