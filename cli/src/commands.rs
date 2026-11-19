//! Subcommand implementations that the `Makefile` and the dashboard call.

use crate::catalog::load_catalog;
use crate::config::active_services;
use crate::docker::compose::{compose_with, ensure_networks, validate_all};
use crate::docker::readiness::ensure_dependencies_ready;
use crate::docker::{label_only_reason, shutdown_queue, startup_queue, Docker};
use crate::env::{self, report, shared};
use crate::{info, stack};
use std::io::{self, BufRead, IsTerminal, Write};
use std::path::{Path, PathBuf};
use std::process::Command;

pub type Res = Result<(), String>;

#[derive(Clone, Copy, PartialEq, Debug)]
pub enum Action {
    Up,
    Down,
    Stop,
    Restart,
    Logs,
}

fn root() -> PathBuf {
    PathBuf::from(".")
}

pub fn say(line: &str) {
    println!("{line}");
}

/// Ask `question`. `force` skips the prompt. A closed or non-TTY stdin answers no.
pub fn confirm(question: &str, force: bool) -> bool {
    if force {
        return true;
    }
    print!("{question} (y/n) ");
    let _ = io::stdout().flush();
    let mut reply = String::new();
    io::stdin().lock().read_line(&mut reply).is_ok()
        && matches!(reply.trim().to_lowercase().as_str(), "y" | "yes")
}

/// Run `docker <args>` with the terminal attached.
pub fn inherit(args: &[String]) -> bool {
    Command::new("docker")
        .args(args)
        .status()
        .is_ok_and(|s| s.success())
}

fn check_service(service: &str) -> Res {
    if active_services().contains(&service) {
        return Ok(());
    }
    Err(format!(
        "Unknown service: {service}\nAvailable services: {}",
        active_services().join(", ")
    ))
}

fn refuse_unconfigured(service: &str, action: &str) -> Res {
    match label_only_reason(&root(), service) {
        Some(reason) => Err(format!("Cannot {action} {service}: {reason}")),
        None => Ok(()),
    }
}

/// Start `service`: prerequisites, networks, backends, then the service.
pub fn start_service(service: &str) -> Res {
    refuse_unconfigured(service, "start")?;
    if !report::check_prerequisites(&root(), Some(service)) {
        return Err(format!(
            "Cannot start {service}: prerequisite checks failed."
        ));
    }
    ensure_networks(&Docker, &say)?;
    if !ensure_dependencies_ready(&Docker, service, &say) {
        return Err(format!(
            "Cannot start {service}: dependencies are not ready."
        ));
    }
    say(&format!("✅ Starting {service}..."));
    if !inherit(&compose_with(service, &["up", "-d"])?) {
        return Err(format!("Failed to start {service}"));
    }
    say(&format!("✅ {service} started successfully"));
    Ok(())
}

fn run_simple(service: &str, verb: &str, progress: &str, done: &str) -> Res {
    say(&format!("ℹ️  {progress} {service}..."));
    if !inherit(&compose_with(service, &[verb])?) {
        return Err(format!("{verb} failed for {service}"));
    }
    say(&format!("✅ {service} {done}"));
    Ok(())
}

/// One lifecycle action on one service.
pub fn service_action(service: &str, action: Action) -> Res {
    check_service(service)?;
    match action {
        Action::Up => start_service(service),
        Action::Down => run_simple(service, "down", "Stopping and removing", "down"),
        Action::Stop => run_simple(service, "stop", "Stopping", "stopped"),
        Action::Restart => {
            refuse_unconfigured(service, "restart")?;
            run_simple(service, "restart", "Restarting", "restarted")
        }
        Action::Logs => {
            say(&format!(
                "ℹ️  Displaying logs for {service} (press Ctrl+C to exit)..."
            ));
            inherit(&compose_with(service, &["logs", "-f"])?);
            Ok(())
        }
    }
}

/// One action on every active service: start in dependency order, stop in reverse.
pub fn all_action(action: Action) -> Res {
    let names: Vec<String> = active_services().iter().map(|s| s.to_string()).collect();
    let order = match action {
        Action::Up | Action::Restart => startup_queue(&names),
        Action::Down | Action::Stop => shutdown_queue(&names),
        Action::Logs => return Err("logs needs --service <name>".into()),
    };
    order
        .iter()
        .try_for_each(|service| service_action(service, action))
}

/// Compose arguments that span every service file, as the old Makefile built them.
pub fn all_services_args() -> Result<Vec<String>, String> {
    let mut args: Vec<String> = vec!["compose".into()];
    let name = stack::stack_name()?;
    if !name.is_empty() {
        args.extend(["-p".into(), name]);
    }
    args.extend(["-f".into(), "docker-compose.shared.yml".into()]);
    let mut dirs: Vec<&str> = active_services()
        .iter()
        .copied()
        .filter(|s| Path::new(s).join("docker-compose.yml").is_file())
        .collect();
    dirs.sort_unstable();
    for dir in dirs {
        args.extend(["-f".into(), format!("{dir}/docker-compose.yml")]);
    }
    Ok(args)
}

pub fn ps() -> Res {
    println!("\nService Status:\n");
    let mut args = all_services_args()?;
    args.push("ps".into());
    inherit(&args);
    println!();
    Ok(())
}

pub fn health(service: Option<&str>) -> Res {
    println!("\nService Health:\n");
    match service {
        Some(s) => {
            check_service(s)?;
            inherit(&compose_with(s, &["ps"])?);
        }
        None => {
            let mut args = all_services_args()?;
            args.extend([
                "ps".into(),
                "--format".into(),
                "table {{.Name}}\t{{.Status}}".into(),
            ]);
            inherit(&args);
        }
    }
    println!();
    Ok(())
}

pub fn show_info() -> Res {
    print!("{}", info::info_text(&load_catalog())?);
    Ok(())
}

/// `docker compose config` for every service. Fails when any is invalid.
pub fn validate() -> Res {
    let failed = validate_all(&Docker, &say);
    if failed.is_empty() {
        say("✅ Compose configuration and service catalog are valid");
        return Ok(());
    }
    Err(format!("Validation failed for: {}", failed.join(", ")))
}

/// Networks, env files, secrets, and Dozzle users. `yes` creates missing `.env` files without asking.
pub fn setup(password: Option<&str>, yes: bool) -> Res {
    let root = root();
    println!("Checking shared Docker networks (names and subnets from SANDBOX_NAME and SANDBOX_SUBNET_BASE)...");
    ensure_networks(&Docker, &say)?;
    println!("Checking environment files...");
    let missing = env::check_env(&root, None);
    let ask = missing && io::stdin().is_terminal();
    if yes
        || (ask
            && confirm(
                "Do you want to create missing .env files from .env.example?",
                false,
            ))
    {
        env::create_env(&root, None);
    }
    env::merge_missing(&root, None);
    shared::fill_shared_password(&root, password, false, false)?;
    shared::fill_secrets(&root, None)?;
    println!("Checking Dozzle users file (dozzle/data/users.yml)...");
    env::dozzle::ensure_dozzle_users(&root.join("dozzle/data/users.yml"), &root.join(".env"))?;
    report::validate_env(&root, None);
    report::show_summary(&root, None);
    Ok(())
}

/// Env sub-commands, as `python -m dss.cli.env` offered them.
pub fn env_command(
    name: &str,
    service: Option<&str>,
    password: Option<&str>,
    force: bool,
    dry_run: bool,
) -> Res {
    let root = root();
    match name {
        "check" => drop(env::check_env(&root, service)),
        "create" => drop(env::create_env(&root, service)),
        "merge-missing" => drop(env::merge_missing(&root, service)),
        "fill-secrets" => drop(shared::fill_secrets(&root, service)?),
        "passwords" => drop(shared::fill_shared_password(
            &root, password, force, dry_run,
        )?),
        "summary" => report::show_summary(&root, service),
        "validate" if !report::validate_env(&root, service) => {
            return Err("validation failed".into())
        }
        "check-prerequisites" if !report::check_prerequisites(&root, service) => {
            return Err("prerequisite checks failed".into())
        }
        _ => {}
    }
    Ok(())
}

/// `dss package`: a non-interactive export with `--name` and `--services`, else the wizard.
pub fn package(name: Option<String>, services: Vec<String>, dest: Option<PathBuf>) -> Res {
    let root = root();
    let done = match name {
        Some(name) => crate::package::export_stack(&services, &name, &root, dest).map(Some)?,
        None => crate::package::wizard_ui::run(&root)?,
    };
    match done {
        Some(path) => println!("✅ Exported to {}", path.display()),
        None => println!("Cancelled"),
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn force_skips_the_prompt() {
        assert!(confirm("anything", true));
    }

    #[test]
    fn unknown_service_lists_the_available_ones() {
        let err = service_action("nope", Action::Up).unwrap_err();
        assert!(err.contains("Unknown service: nope") && err.contains("zitadel"));
    }

    #[test]
    fn all_services_args_start_with_the_shared_file() {
        let args = all_services_args().unwrap();
        assert_eq!(&args[..3], ["compose", "-f", "docker-compose.shared.yml"]);
    }
}
