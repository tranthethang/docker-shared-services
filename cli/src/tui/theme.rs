//! 24-bit RGB theme tokens for the TUI dashboard (`DSS_THEME`).

use ratatui::style::Color;

/// Color palette for the Local Infrastructure Cockpit.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct Theme {
    pub surface_base: Color,
    pub surface_elevated: Color,
    pub border_muted: Color,
    pub border_focus: Color,
    pub text_primary: Color,
    pub text_muted: Color,
    pub green: Color,
    pub amber: Color,
    pub red: Color,
}

impl Default for Theme {
    fn default() -> Self {
        Self::ocean()
    }
}

impl Theme {
    /// Default dark slate/sky palette (`ocean`).
    pub const fn ocean() -> Self {
        Self {
            surface_base: Color::Rgb(0x0F, 0x14, 0x19),
            surface_elevated: Color::Rgb(0x16, 0x1E, 0x27),
            border_muted: Color::Rgb(0x2B, 0x37, 0x46),
            border_focus: Color::Rgb(0x38, 0xBD, 0xF8),
            text_primary: Color::Rgb(0xE6, 0xED, 0xF3),
            text_muted: Color::Rgb(0x6E, 0x7B, 0x8B),
            green: Color::Rgb(0x22, 0xC5, 0x5E),
            amber: Color::Rgb(0xF5, 0x9E, 0x0B),
            red: Color::Rgb(0xEF, 0x44, 0x44),
        }
    }

    /// Warm amber-accented dark palette (`amber`).
    pub const fn amber() -> Self {
        Self {
            surface_base: Color::Rgb(0x14, 0x11, 0x0E),
            surface_elevated: Color::Rgb(0x1D, 0x18, 0x13),
            border_muted: Color::Rgb(0x3D, 0x32, 0x26),
            border_focus: Color::Rgb(0xF5, 0x9E, 0x0B),
            text_primary: Color::Rgb(0xF5, 0xEF, 0xE6),
            text_muted: Color::Rgb(0x8C, 0x7E, 0x6E),
            green: Color::Rgb(0x22, 0xC5, 0x5E),
            amber: Color::Rgb(0xF5, 0x9E, 0x0B),
            red: Color::Rgb(0xEF, 0x44, 0x44),
        }
    }

    /// Arctic Nord palette (`nord`).
    pub const fn nord() -> Self {
        Self {
            surface_base: Color::Rgb(0x2E, 0x34, 0x40),
            surface_elevated: Color::Rgb(0x3B, 0x42, 0x52),
            border_muted: Color::Rgb(0x4C, 0x56, 0x6A),
            border_focus: Color::Rgb(0x88, 0xC0, 0xD0),
            text_primary: Color::Rgb(0xEC, 0xEF, 0xF4),
            text_muted: Color::Rgb(0x9A, 0xA5, 0xB8),
            green: Color::Rgb(0xA3, 0xBE, 0x8C),
            amber: Color::Rgb(0xEB, 0xCB, 0x8B),
            red: Color::Rgb(0xBF, 0x61, 0x6A),
        }
    }

    /// Resolve a theme by name (`ocean`, `amber`, `nord`), falling back to `ocean`.
    pub fn from_name(name: &str) -> Self {
        match name.trim().to_ascii_lowercase().as_str() {
            "amber" => Self::amber(),
            "nord" => Self::nord(),
            _ => Self::ocean(),
        }
    }

    /// Read `DSS_THEME` from the environment, defaulting to `ocean`.
    pub fn from_env() -> Self {
        std::env::var("DSS_THEME")
            .map(|v| Self::from_name(&v))
            .unwrap_or_else(|_| Self::ocean())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn resolves_named_palettes_and_falls_back_to_ocean() {
        assert_eq!(Theme::from_name("ocean"), Theme::ocean());
        assert_eq!(Theme::from_name("amber"), Theme::amber());
        assert_eq!(Theme::from_name("nord"), Theme::nord());
        assert_eq!(Theme::from_name("unknown"), Theme::ocean());
        assert_ne!(Theme::amber().border_focus, Theme::nord().border_focus);
    }
}
