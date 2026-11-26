//! Secret generation: hex, sk-hex, base64, htpasswd (bcrypt), HS256 JWT, and passwords.

use super::tables::Method;
use crate::config::{PASSWORD_MIN_LENGTH, PASSWORD_SPECIALS};
use base64::engine::general_purpose::{STANDARD, URL_SAFE_NO_PAD};
use base64::Engine;
use hmac::{Hmac, Mac};
use rand::seq::SliceRandom;
use rand::{Rng, RngCore};
use sha2::Sha256;

const BCRYPT_COST: u32 = 10;
pub const JWT_LIFETIME_SECONDS: u64 = 10 * 365 * 24 * 3600;

fn random_bytes(n: usize) -> Vec<u8> {
    let mut buf = vec![0u8; n];
    rand::thread_rng().fill_bytes(&mut buf);
    buf
}

fn to_hex(bytes: &[u8]) -> String {
    bytes.iter().map(|b| format!("{b:02x}")).collect()
}

/// A random password with a lowercase, uppercase, digit, and special character.
pub fn generate_password(length: usize) -> String {
    let length = length.max(PASSWORD_MIN_LENGTH);
    let pools: [&str; 4] = [
        "abcdefghijklmnopqrstuvwxyz",
        "ABCDEFGHIJKLMNOPQRSTUVWXYZ",
        "0123456789",
        PASSWORD_SPECIALS,
    ];
    let all: Vec<char> = pools.iter().flat_map(|p| p.chars()).collect();
    let mut rng = rand::thread_rng();
    let mut chars: Vec<char> = pools
        .iter()
        .map(|p| p.chars().nth(rng.gen_range(0..p.len())).unwrap())
        .collect();
    while chars.len() < length {
        chars.push(all[rng.gen_range(0..all.len())]);
    }
    chars.shuffle(&mut rng);
    let special = |c: &char| PASSWORD_SPECIALS.contains(*c);
    if special(&chars[0]) {
        // Avoid a leading special character such as "-", which a CLI parses as a flag.
        let idx = chars.iter().position(|c| !special(c)).unwrap();
        chars.swap(0, idx);
    }
    chars.into_iter().collect()
}

/// `user:hash` with a bcrypt hash, `$` doubled for Docker Compose `.env` files.
pub fn bcrypt_auth(username: &str, password: &str) -> Result<String, String> {
    let hash = bcrypt::hash(password, BCRYPT_COST).map_err(|e| e.to_string())?;
    // Traefik and htpasswd tooling accept the `$2y$` prefix.
    let hash = hash.replacen("$2b$", "$2y$", 1);
    Ok(format!("{username}:{hash}").replace('$', "$$"))
}

fn b64url(data: &[u8]) -> String {
    URL_SAFE_NO_PAD.encode(data)
}

/// Sign a Supabase API key (HS256 JWT) for `role`.
pub fn generate_hs256_jwt(secret: &str, role: &str, now: u64) -> String {
    let header = r#"{"alg":"HS256","typ":"JWT"}"#;
    let payload = format!(
        r#"{{"role":"{role}","iss":"supabase","iat":{now},"exp":{}}}"#,
        now + JWT_LIFETIME_SECONDS
    );
    let input = format!(
        "{}.{}",
        b64url(header.as_bytes()),
        b64url(payload.as_bytes())
    );
    let mut mac =
        Hmac::<Sha256>::new_from_slice(secret.as_bytes()).expect("HMAC takes any key length");
    mac.update(input.as_bytes());
    format!("{input}.{}", b64url(&mac.finalize().into_bytes()))
}

/// Generate one local secret. `password` feeds `Htpasswd`.
pub fn generate_secret(method: Method, nbytes: usize, password: &str) -> Result<String, String> {
    match method {
        Method::Hex => Ok(to_hex(&random_bytes(nbytes))),
        Method::Base64 => Ok(STANDARD.encode(random_bytes(nbytes))),
        Method::Htpasswd => bcrypt_auth("admin", password),
        Method::JwtHs256 => Err("jwt_hs256 needs a role; call generate_hs256_jwt".into()),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::config::validate_password_strength;

    #[test]
    fn hex_has_two_chars_per_byte() {
        let v = generate_secret(Method::Hex, 16, "").unwrap();
        assert_eq!(v.len(), 32);
        assert!(v.chars().all(|c| c.is_ascii_hexdigit()));
        assert_eq!(generate_secret(Method::Hex, 8, "").unwrap().len(), 16);
    }

    #[test]
    fn base64_decodes_to_nbytes() {
        let v = generate_secret(Method::Base64, 50, "").unwrap();
        assert_eq!(STANDARD.decode(v).unwrap().len(), 50);
    }

    #[test]
    fn htpasswd_is_escaped_bcrypt_that_verifies() {
        let v = generate_secret(Method::Htpasswd, 16, "Sup3r-Secret-pw!").unwrap();
        let hash = v.strip_prefix("admin:").unwrap();
        assert!(hash.starts_with("$$2y$$10$$"), "{hash}");
        let raw = hash.replace("$$", "$").replacen("$2y$", "$2b$", 1);
        assert!(bcrypt::verify("Sup3r-Secret-pw!", &raw).unwrap());
    }

    #[test]
    fn jwt_has_three_parts_role_and_valid_signature() {
        let token = generate_hs256_jwt("topsecret", "anon", 1_000);
        let parts: Vec<&str> = token.split('.').collect();
        assert_eq!(parts.len(), 3);
        let payload = String::from_utf8(URL_SAFE_NO_PAD.decode(parts[1]).unwrap()).unwrap();
        assert!(payload.contains(r#""role":"anon""#));
        assert!(payload.contains(&format!(r#""exp":{}"#, 1_000 + JWT_LIFETIME_SECONDS)));
        let mut mac = Hmac::<Sha256>::new_from_slice(b"topsecret").unwrap();
        mac.update(format!("{}.{}", parts[0], parts[1]).as_bytes());
        assert_eq!(b64url(&mac.finalize().into_bytes()), parts[2]);
    }

    #[test]
    fn generated_password_is_strong_and_does_not_lead_with_special() {
        for _ in 0..50 {
            let p = generate_password(32);
            assert_eq!(p.len(), 32);
            assert_eq!(validate_password_strength(&p), None, "{p}");
            assert!(!PASSWORD_SPECIALS.contains(p.chars().next().unwrap()));
        }
        assert_eq!(generate_password(3).len(), PASSWORD_MIN_LENGTH);
    }
}
