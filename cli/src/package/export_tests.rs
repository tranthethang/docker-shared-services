use super::*;

fn names(items: &[&str]) -> Vec<String> {
    items.iter().map(|s| s.to_string()).collect()
}

/// The repo root, found from the crate directory.
fn repo() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .unwrap()
        .to_path_buf()
}

fn temp(label: &str) -> PathBuf {
    let dir = std::env::temp_dir().join(format!("dss-export-{label}-{}", std::process::id()));
    let _ = fs::remove_dir_all(&dir);
    fs::create_dir_all(&dir).unwrap();
    dir
}

#[test]
fn stack_names_follow_the_pattern() {
    for ok in ["a", "demo", "my-stack-2", "a1-b2"] {
        assert!(validate_stack_name(ok).is_ok(), "{ok}");
    }
    for bad in [
        "",
        "Demo",
        "1abc",
        "a--b",
        "-a",
        "a-",
        "a_b",
        &"x".repeat(49),
    ] {
        assert!(validate_stack_name(bad).is_err(), "{bad}");
    }
}

#[test]
fn resolves_backends_and_traefik_in_service_order() {
    let all = resolve_services(&names(&["hindsight"]), &repo()).unwrap();
    assert!(all.contains(&"pgvector".to_string()) && all.contains(&"traefik".to_string()));
    let pos = |n: &str| all.iter().position(|s| s == n).unwrap();
    assert!(
        pos("hindsight") < pos("pgvector") && pos("pgvector") < pos("traefik"),
        "SERVICES order"
    );
    assert_eq!(
        resolve_services(&names(&["inngest"]), &repo())
            .unwrap()
            .iter()
            .filter(|s| *s == "postgres" || *s == "redis")
            .count(),
        2
    );
}

#[test]
fn rejects_unknown_and_empty_selections() {
    assert!(resolve_services(&names(&["nope"]), &repo())
        .unwrap_err()
        .contains("Unknown services: nope"));
    assert!(resolve_services(&[], &repo())
        .unwrap_err()
        .contains("No services"));
}

#[test]
fn partition_separates_added_dependencies() {
    let (checked, added) = partition_selection(&names(&["garage_ui"]), &repo()).unwrap();
    assert_eq!(checked, ["garage_ui"]);
    assert!(added.contains(&"garage".to_string()));
}

#[test]
fn exporting_one_service_writes_its_dependencies_and_traefik() {
    let out = temp("one").join("stack");
    let dest = export_stack(&names(&["hindsight"]), "demo", &repo(), Some(out)).unwrap();
    for dir in ["hindsight", "pgvector", "traefik"] {
        assert!(dest.join(dir).join("docker-compose.yml").is_file(), "{dir}");
    }
    for file in [
        "docker-compose.shared.yml",
        ".env.example",
        "Makefile",
        "README.md",
        ".gitignore",
        "dss-package.json",
        "cli/Cargo.toml",
        "cli/Cargo.lock",
        "cli/src/main.rs",
        "cli/service_catalog.json",
    ] {
        assert!(dest.join(file).is_file(), "{file}");
    }
}

#[test]
fn unrelated_services_are_absent_from_the_export() {
    let out = temp("filter").join("stack");
    let dest = export_stack(&names(&["redis"]), "demo", &repo(), Some(out)).unwrap();
    assert!(!dest.join("postgres").exists() && !dest.join("mailpit").exists());
    let env = fs::read_to_string(dest.join(".env.example")).unwrap();
    assert!(
        env.contains("REDIS_PORT")
            && !env.contains("POSTGRES16_PORT")
            && !env.contains("MAILPIT_PORT")
    );
    let manifest = fs::read_to_string(dest.join("dss-package.json")).unwrap();
    assert!(manifest.contains("redis") && !manifest.contains("postgres"));
    let catalog = fs::read_to_string(dest.join("cli/service_catalog.json")).unwrap();
    assert!(catalog.contains("\"redis\"") && !catalog.contains("\"postgres\""));
    assert!(!fs::read_to_string(dest.join("README.md"))
        .unwrap()
        .contains("postgres"));
}

#[test]
fn export_skips_env_files_data_dirs_and_target() {
    let out = temp("skip").join("stack");
    let dest = export_stack(&names(&["redis"]), "demo", &repo(), Some(out)).unwrap();
    assert!(!dest.join("redis/.env").exists());
    assert!(!dest.join("cli/target").exists());
    assert!(!dest.join("redis/data").exists());
}

#[test]
fn refuses_an_existing_destination_and_a_bad_name() {
    let out = temp("exists");
    assert!(
        export_stack(&names(&["redis"]), "demo", &repo(), Some(out.clone()))
            .unwrap_err()
            .contains("already exists")
    );
    assert!(export_stack(&names(&["redis"]), "Bad Name", &repo(), Some(out.join("x"))).is_err());
}

#[test]
fn failure_removes_the_partial_tree() {
    let fake_root = temp("fakeroot");
    let dest = temp("partial").join("stack");
    assert!(export_stack(&names(&["redis"]), "demo", &fake_root, Some(dest.clone())).is_err());
    assert!(!dest.exists());
}

#[test]
fn skip_rules() {
    assert!(skip_dir("data") && skip_dir("pg_data") && !skip_dir("config"));
    assert!(skip_file("redis", Path::new(".env")));
    assert!(skip_file("traefik", Path::new("certs/a.crt")));
    assert!(!skip_file("redis", Path::new("certs/a.crt")));
    assert!(!skip_file("redis", Path::new(".env.example")));
}
