use super::*;
use std::path::PathBuf;

fn repo() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .unwrap()
        .to_path_buf()
}

fn key(c: char) -> KeyEvent {
    KeyEvent::new(KeyCode::Char(c), KeyModifiers::NONE)
}

fn press(w: &mut Wizard, code: KeyCode) -> Outcome {
    w.on_key(KeyEvent::new(code, KeyModifiers::NONE), &repo())
}

fn type_name(w: &mut Wizard, text: &str) {
    text.chars().for_each(|c| drop(w.on_key(key(c), &repo())));
}

#[test]
fn opens_with_the_default_services_checked() {
    let w = Wizard::new();
    assert_eq!(w.step, Step::Select);
    assert!(
        w.checked.contains("traefik")
            && w.checked.contains("postgres")
            && !w.checked.contains("gitea")
    );
}

#[test]
fn space_toggles_and_a_c_select_all_or_clear() {
    let mut w = Wizard::new();
    let before = w.checked.len();
    press(&mut w, KeyCode::Char(' '));
    assert_ne!(w.checked.len(), before);
    w.on_key(key('a'), &repo());
    assert_eq!(w.checked.len(), w.items.len());
    w.on_key(key('c'), &repo());
    assert!(w.checked.is_empty());
    press(&mut w, KeyCode::Enter);
    assert_eq!(w.step, Step::Select);
    assert!(w.error.contains("at least one"));
}

#[test]
fn name_step_validates_before_moving_on() {
    let mut w = Wizard::new();
    press(&mut w, KeyCode::Enter);
    assert_eq!(w.step, Step::Name);
    type_name(&mut w, "Bad Name");
    press(&mut w, KeyCode::Enter);
    assert_eq!(w.step, Step::Name);
    assert!(w.error.contains("Stack name"));
    (0..8).for_each(|_| drop(press(&mut w, KeyCode::Backspace)));
    type_name(&mut w, "demo");
    press(&mut w, KeyCode::Enter);
    assert_eq!(w.step, Step::Confirm);
}

#[test]
fn confirm_returns_services_with_dependencies_and_name() {
    let mut w = Wizard::new();
    w.on_key(key('c'), &repo());
    w.cursor = w.items.iter().position(|s| *s == "hindsight").unwrap();
    press(&mut w, KeyCode::Char(' '));
    press(&mut w, KeyCode::Enter);
    type_name(&mut w, "demo");
    press(&mut w, KeyCode::Enter);
    let Outcome::Export(services, name) = press(&mut w, KeyCode::Char('y')) else {
        panic!("expected export")
    };
    assert_eq!(name, "demo");
    assert!(
        services.contains(&"hindsight".to_string())
            && services.contains(&"pgvector".to_string())
            && services.contains(&"traefik".to_string())
    );
}

#[test]
fn n_goes_back_and_q_cancels() {
    let mut w = Wizard::new();
    press(&mut w, KeyCode::Enter);
    type_name(&mut w, "demo");
    press(&mut w, KeyCode::Enter);
    press(&mut w, KeyCode::Char('n'));
    assert_eq!(w.step, Step::Name);
    press(&mut w, KeyCode::Esc);
    assert_eq!(w.step, Step::Select);
    assert_eq!(press(&mut w, KeyCode::Char('q')), Outcome::Cancel);
}
