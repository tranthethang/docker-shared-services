mod catalog;
mod cleanup;
mod commands;
mod config;
mod docker;
mod env;
mod info;
mod package;
#[cfg(test)]
mod repo_rules;
#[cfg(test)]
mod size_rules;
mod stack;
mod tui;

use clap::{Parser, Subcommand};
use commands::Action;

#[derive(Parser)]
#[command(name = "dss", about = "Docker shared services manager")]
struct Cli {
    #[command(subcommand)]
    command: Option<Command>,
}

#[derive(Subcommand)]
enum Command {
    /// Create networks and env files, fill secrets, and write Dozzle users.
    Setup {
        /// Shared password (default: DSS_SHARED_PASSWORD, the root .env value, or a new one).
        #[arg(long)]
        password: Option<String>,
        /// Create missing .env files without asking.
        #[arg(short, long)]
        yes: bool,
    },
    /// Start a service after its backends are ready.
    Up(Target),
    /// Stop and remove a service.
    Down(Target),
    /// Stop a service.
    Stop(Target),
    /// Restart a service.
    Restart(Target),
    /// Follow a service's logs.
    Logs(Target),
    /// Show the status of all services.
    Ps,
    /// Show health for one service, or all.
    Health(Target),
    /// Show service URLs and networks.
    Info,
    /// Run `docker compose config` for every service.
    Validate,
    /// Manage env files and secrets.
    Env {
        #[arg(value_parser = ["check", "create", "merge-missing", "fill-secrets", "passwords", "validate", "summary", "check-prerequisites"])]
        command: String,
        #[arg(short, long)]
        service: Option<String>,
        #[arg(long)]
        password: Option<String>,
        /// Overwrite non-placeholder passwords.
        #[arg(long)]
        force: bool,
        #[arg(long)]
        dry_run: bool,
    },
    /// Remove every container and volume.
    Teardown(Force),
    /// Remove unused Docker resources.
    Prune(Force),
    /// Remove .env files that have a matching .env.example.
    RemoveConfig(Force),
    /// Export a service subset to dist/<name>/ (opens a wizard without flags).
    Package {
        /// Stack name, for a non-interactive export.
        #[arg(long, requires = "services")]
        name: Option<String>,
        /// Comma-separated services, for a non-interactive export.
        #[arg(long, value_delimiter = ',', requires = "name")]
        services: Vec<String>,
        /// Write here in place of dist/<name>.
        #[arg(long)]
        dest: Option<std::path::PathBuf>,
    },
    /// Print the stack name, or the shared network `name:subnet` pairs.
    Stack {
        #[arg(long)]
        name: bool,
    },
}

#[derive(clap::Args)]
struct Target {
    /// Service name.
    #[arg(short, long)]
    service: Option<String>,
    /// Apply to every service of this stack, in dependency order.
    #[arg(long, conflicts_with = "service")]
    all: bool,
}

#[derive(clap::Args)]
struct Force {
    /// Skip the confirmation prompt.
    #[arg(short, long)]
    force: bool,
}

fn need(target: Target, verb: &str) -> Result<String, String> {
    target
        .service
        .ok_or_else(|| format!("{verb} needs --service <name>"))
}

fn lifecycle(target: Target, action: Action, verb: &str) -> Result<(), String> {
    if target.all {
        return commands::all_action(action);
    }
    commands::service_action(&need(target, verb)?, action)
}

fn print_line(text: &str) -> Result<(), String> {
    println!("{text}");
    Ok(())
}

fn run(cli: Cli) -> Result<(), String> {
    use Command::*;
    match cli.command {
        Some(Setup { password, yes }) => commands::setup(password.as_deref(), yes),
        Some(Up(t)) => lifecycle(t, Action::Up, "up"),
        Some(Down(t)) => lifecycle(t, Action::Down, "down"),
        Some(Stop(t)) => lifecycle(t, Action::Stop, "stop"),
        Some(Restart(t)) => lifecycle(t, Action::Restart, "restart"),
        Some(Logs(t)) => lifecycle(t, Action::Logs, "logs"),
        Some(Ps) => commands::ps(),
        Some(Health(t)) => commands::health(t.service.as_deref()),
        Some(Info) => commands::show_info(),
        Some(Validate) => commands::validate(),
        Some(Env {
            command,
            service,
            password,
            force,
            dry_run,
        }) => commands::env_command(
            &command,
            service.as_deref(),
            password.as_deref(),
            force,
            dry_run,
        ),
        Some(Package {
            name,
            services,
            dest,
        }) => commands::package(name, services, dest),
        Some(Teardown(f)) => cleanup::teardown(f.force),
        Some(Prune(f)) => cleanup::prune(f.force),
        Some(RemoveConfig(f)) => cleanup::remove_config(f.force),
        Some(Stack { name: true }) => print_line(&stack::stack_name()?),
        Some(Stack { name: false }) => print_line(&stack::network_pairs()?.join("\n")),
        None => tui::run(),
    }
}

fn main() {
    if let Err(message) = run(Cli::parse()) {
        eprintln!("❌ {message}");
        std::process::exit(1);
    }
}
