//! Container stats, Docker VM capacity, and disk usage parsers and collectors.

use super::Runner;
use std::collections::BTreeMap;

/// Live CPU and memory usage for one container (`docker stats --no-stream`).
#[derive(Debug, Clone, PartialEq, Default)]
pub struct ContainerStat {
    pub name: String,
    pub cpu_pct: f64,
    pub mem_used_bytes: u64,
    pub mem_limit_bytes: u64,
    pub mem_pct: f64,
}

/// Docker VM / daemon CPU and memory capacity (`docker info`).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub struct DockerCapacity {
    pub ncpu: u32,
    pub mem_total_bytes: u64,
}

/// Docker disk usage summary (`docker system df`).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub struct DiskUsage {
    pub images_bytes: u64,
    pub containers_bytes: u64,
    pub volumes_bytes: u64,
    pub total_bytes: u64,
    pub reclaimable_bytes: u64,
}

/// Parse a Docker human-readable byte string (`MiB`, `GiB`, `KiB`, `MB`, `GB`, `KB`, `B`).
pub fn parse_bytes(raw: &str) -> Option<u64> {
    let trimmed = raw.split('(').next()?.trim();
    if trimmed.is_empty() || trimmed == "--" {
        return None;
    }
    let split_at = trimmed
        .find(|c: char| !c.is_ascii_digit() && c != '.')
        .unwrap_or(trimmed.len());
    let (num_str, unit) = trimmed.split_at(split_at);
    let value: f64 = num_str.trim().parse().ok()?;
    if !value.is_finite() || value < 0.0 {
        return None;
    }
    let mult: f64 = match unit.trim() {
        "" | "B" => 1.0,
        "KiB" | "kiB" => 1024.0,
        "MiB" => 1024.0 * 1024.0,
        "GiB" => 1024.0 * 1024.0 * 1024.0,
        "TiB" => 1024.0 * 1024.0 * 1024.0 * 1024.0,
        "KB" | "kB" => 1000.0,
        "MB" => 1000.0 * 1000.0,
        "GB" => 1000.0 * 1000.0 * 1000.0,
        "TB" => 1000.0 * 1000.0 * 1000.0 * 1000.0,
        _ => return None,
    };
    Some((value * mult).round() as u64)
}

fn parse_pct(raw: &str) -> Option<f64> {
    let trimmed = raw.trim().trim_end_matches('%').trim();
    if trimmed.is_empty() || trimmed == "--" {
        return None;
    }
    let val: f64 = trimmed.parse().ok()?;
    val.is_finite().then_some(val)
}

/// Parse one line of `docker stats --no-stream --format "{{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}"`.
pub fn parse_stats_line(line: &str) -> Option<ContainerStat> {
    let fields: Vec<&str> = line.trim_end().split('\t').collect();
    if fields.len() < 4 {
        return None;
    }
    let name = fields[0].trim_start_matches('/').trim().to_string();
    if name.is_empty() {
        return None;
    }
    let (used_str, limit_str) = fields[2].split_once('/').unwrap_or((fields[2], ""));
    Some(ContainerStat {
        name,
        cpu_pct: parse_pct(fields[1]).unwrap_or(0.0),
        mem_used_bytes: parse_bytes(used_str).unwrap_or(0),
        mem_limit_bytes: parse_bytes(limit_str).unwrap_or(0),
        mem_pct: parse_pct(fields[3]).unwrap_or(0.0),
    })
}

/// Parse all lines from `docker stats --no-stream`.
pub fn parse_stats(stdout: &str) -> BTreeMap<String, ContainerStat> {
    stdout
        .lines()
        .filter_map(parse_stats_line)
        .map(|s| (s.name.clone(), s))
        .collect()
}

/// Parse `docker info --format "{{.NCPU}}\t{{.MemTotal}}"`.
pub fn parse_capacity(stdout: &str) -> Option<DockerCapacity> {
    let line = stdout.lines().find(|l| !l.trim().is_empty())?;
    let (cpu_str, mem_str) = line.trim().split_once('\t')?;
    let ncpu = cpu_str.trim().parse::<u32>().ok()?;
    let mem_total_bytes = mem_str.trim().parse::<u64>().ok()?;
    Some(DockerCapacity {
        ncpu,
        mem_total_bytes,
    })
}

/// Parse `docker system df --format "{{.Type}}\t{{.Size}}\t{{.Reclaimable}}"`.
pub fn parse_disk_usage(stdout: &str) -> DiskUsage {
    let mut df = DiskUsage::default();
    for line in stdout.lines() {
        let fields: Vec<&str> = line.trim_end().split('\t').collect();
        if fields.len() < 3 {
            continue;
        }
        let size = parse_bytes(fields[1]).unwrap_or(0);
        let reclaimable = parse_bytes(fields[2]).unwrap_or(0);
        df.total_bytes = df.total_bytes.saturating_add(size);
        df.reclaimable_bytes = df.reclaimable_bytes.saturating_add(reclaimable);
        match fields[0].trim() {
            "Images" => df.images_bytes = size,
            "Containers" => df.containers_bytes = size,
            "Local Volumes" => df.volumes_bytes = size,
            _ => {}
        }
    }
    df
}

/// Collect live container stats via `docker stats --no-stream`.
pub fn collect_stats(runner: &dyn Runner) -> Result<BTreeMap<String, ContainerStat>, String> {
    let args = vec![
        "stats".into(),
        "--no-stream".into(),
        "--format".into(),
        "{{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}".into(),
    ];
    let out = runner.run(&args);
    if !out.ok {
        return Err(out.stderr.trim().to_string());
    }
    Ok(parse_stats(&out.stdout))
}

/// Collect Docker VM capacity via `docker info`.
pub fn collect_capacity(runner: &dyn Runner) -> Result<DockerCapacity, String> {
    let args = vec![
        "info".into(),
        "--format".into(),
        "{{.NCPU}}\t{{.MemTotal}}".into(),
    ];
    let out = runner.run(&args);
    if !out.ok {
        return Err(out.stderr.trim().to_string());
    }
    parse_capacity(&out.stdout).ok_or_else(|| "Unable to parse docker info capacity".into())
}

/// Collect Docker disk usage via `docker system df`.
pub fn collect_disk_usage(runner: &dyn Runner) -> Result<DiskUsage, String> {
    let args = vec![
        "system".into(),
        "df".into(),
        "--format".into(),
        "{{.Type}}\t{{.Size}}\t{{.Reclaimable}}".into(),
    ];
    let out = runner.run(&args);
    if !out.ok {
        return Err(out.stderr.trim().to_string());
    }
    Ok(parse_disk_usage(&out.stdout))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parses_byte_units() {
        assert_eq!(parse_bytes("512B"), Some(512));
        assert_eq!(parse_bytes("1KiB"), Some(1024));
        assert_eq!(parse_bytes("2.5MiB"), Some(2_621_440));
        assert_eq!(parse_bytes("1GiB"), Some(1_073_741_824));
        assert_eq!(parse_bytes("4.2GB"), Some(4_200_000_000));
        assert_eq!(parse_bytes("12.4MB"), Some(12_400_000));
        assert_eq!(parse_bytes("1.5GB (35%)"), Some(1_500_000_000));
        assert_eq!(parse_bytes("--"), None);
        assert_eq!(parse_bytes(""), None);
    }

    #[test]
    fn parses_stats_lines_and_ignores_malformed() {
        let raw = "/postgres\t1.25%\t64MiB / 2GiB\t3.12%\nbad line\nredis\t--\t-- / --\t--\n";
        let map = parse_stats(raw);
        assert_eq!(map.len(), 2);
        let pg = &map["postgres"];
        assert!((pg.cpu_pct - 1.25).abs() < 1e-6);
        assert_eq!(pg.mem_used_bytes, 64 * 1024 * 1024);
        assert_eq!(pg.mem_limit_bytes, 2 * 1024 * 1024 * 1024);
        assert_eq!(map["redis"].cpu_pct, 0.0);
        assert_eq!(map["redis"].mem_used_bytes, 0);
    }

    #[test]
    fn parses_capacity_and_disk_usage() {
        let cap = parse_capacity("8\t8345677824\n").unwrap();
        assert_eq!(cap.ncpu, 8);
        assert_eq!(cap.mem_total_bytes, 8_345_677_824);
        assert!(parse_capacity("bad").is_none());

        let df = parse_disk_usage(
            "Images\t4GB\t1.5GB (37%)\nContainers\t10MB\t0B (0%)\nLocal Volumes\t500MB\t100MB (20%)\n",
        );
        assert_eq!(df.images_bytes, 4_000_000_000);
        assert_eq!(df.containers_bytes, 10_000_000);
        assert_eq!(df.volumes_bytes, 500_000_000);
        assert_eq!(df.total_bytes, 4_510_000_000);
        assert_eq!(df.reclaimable_bytes, 1_600_000_000);
    }
}
