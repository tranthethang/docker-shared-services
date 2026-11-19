//! The 300-line limit for every Rust and shell source file in the repo.

use std::fs;
use std::path::{Path, PathBuf};

const LIMIT: usize = 300;

fn repo() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .unwrap()
        .to_path_buf()
}

fn source_files(dir: &Path, out: &mut Vec<PathBuf>) {
    for entry in fs::read_dir(dir).into_iter().flatten().flatten() {
        let path = entry.path();
        let name = entry.file_name();
        if path.is_dir() {
            if !matches!(
                name.to_str(),
                Some(
                    "target" | "data" | ".git" | "dist" | ".venv" | ".agent-relay" | "node_modules"
                )
            ) {
                source_files(&path, out);
            }
        } else if path.extension().is_some_and(|e| e == "rs" || e == "sh") {
            out.push(path);
        }
    }
}

#[test]
fn every_source_file_is_within_the_line_limit() {
    let mut files = Vec::new();
    source_files(&repo(), &mut files);
    let over: Vec<String> = files
        .iter()
        .filter_map(|p| {
            let lines = fs::read_to_string(p).ok()?.lines().count();
            (lines > LIMIT)
                .then(|| format!("{}: {lines} lines exceeds limit of {LIMIT}", p.display()))
        })
        .collect();
    assert!(over.is_empty(), "{over:#?}");
}
