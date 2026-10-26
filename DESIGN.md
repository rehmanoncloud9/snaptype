---
name: Obsidian Cyber-Glass
colors:
  surface: '#0e141b'
  surface-dim: '#0e141b'
  surface-bright: '#333a41'
  surface-container-lowest: '#080f15'
  surface-container-low: '#161c23'
  surface-container: '#1a2027'
  surface-container-high: '#242b32'
  surface-container-highest: '#2f353d'
  on-surface: '#dde3ed'
  on-surface-variant: '#b9cacb'
  inverse-surface: '#dde3ed'
  inverse-on-surface: '#2b3139'
  outline: '#849495'
  outline-variant: '#3a494b'
  surface-tint: '#00dce7'
  primary: '#dcfdff'
  on-primary: '#00373a'
  primary-container: '#00f1fd'
  on-primary-container: '#006a6f'
  inverse-primary: '#00696f'
  secondary: '#deb7ff'
  on-secondary: '#41215e'
  secondary-container: '#583876'
  on-secondary-container: '#cca6ed'
  tertiary: '#f2f6ff'
  on-tertiary: '#2a3139'
  tertiary-container: '#d3dae5'
  on-tertiary-container: '#586068'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#70f6ff'
  primary-fixed-dim: '#00dce7'
  on-primary-fixed: '#002022'
  on-primary-fixed-variant: '#004f53'
  secondary-fixed: '#f1dbff'
  secondary-fixed-dim: '#deb7ff'
  on-secondary-fixed: '#2a0847'
  on-secondary-fixed-variant: '#583876'
  tertiary-fixed: '#dce3ed'
  tertiary-fixed-dim: '#c0c7d1'
  on-tertiary-fixed: '#151c24'
  on-tertiary-fixed-variant: '#404750'
  background: '#0e141b'
  on-background: '#dde3ed'
  surface-variant: '#2f353d'
  surface-lowest: '#080f16'
  surface-panel: rgba(255, 255, 255, 0.03)
  surface-clay: rgba(255, 255, 255, 0.07)
  glow-cyan: rgba(0, 220, 230, 0.3)
  glow-purple: rgba(162, 88, 231, 0.3)
  border-white-low: rgba(255, 255, 255, 0.05)
typography:
  display:
    fontFamily: Inter
    fontSize: 48px
    fontWeight: '700'
    lineHeight: '1.1'
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Inter
    fontSize: 32px
    fontWeight: '600'
    lineHeight: '1.2'
    letterSpacing: -0.01em
  headline-lg-mobile:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: '1.2'
  headline-md:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: '1.3'
  headline-sm:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '600'
    lineHeight: '1.4'
  body-lg:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: '1.6'
  body-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: '1.5'
  label-md:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '500'
    lineHeight: '1'
    letterSpacing: 0.05em
  mono-label:
    fontFamily: Geist Mono
    fontSize: 12px
    fontWeight: '400'
    lineHeight: '1'
    letterSpacing: 0.1em
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  unit: 4px
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
  xl: 48px
  gutter: 20px
  margin-mobile: 16px
  margin-desktop: 32px
---

## Brand & Style
The brand personality is high-performance, technical, and premium. It targets power users and developers who value speed and efficiency. The design style is **Glassmorphism mixed with Tactile Cyberpunk**, characterized by deep obsidian surfaces, vibrant neon accents (Cyan and Purple), and soft, frosted-glass panels. The UI should feel like a futuristic command deck—precise, immersive, and highly responsive. Visual hierarchy is driven by glow effects and varying levels of translucency rather than flat color blocks.

## Colors
The palette is rooted in an ultra-dark obsidian (`#080f16`) background. Primary interactions use a vibrant **Electric Cyan** (`#00f1fd`), while secondary metrics and creative actions use **Soft Amethyst** (`#deb7ff`). 

Gradients are essential: 
- **Cyan Gradient:** `#00f1fd` to `#006a6f`
- **Purple Gradient:** `#deb7ff` to `#a258e7`

Semantic colors are used sparingly, with the cyan double-hatting as a "System Online" or "Success" indicator. Borders should almost always be low-opacity white (`rgba(255, 255, 255, 0.05)`) to maintain the glass effect without creating hard visual breaks.

## Typography
The system uses **Inter** for all functional and display text to maintain a clean, neutral, and highly legible aesthetic. To lean into the technical brand identity, **Geist Mono** is utilized for specialized metadata, system statuses, and micro-labels. 

Display styles should use tight tracking and bold weights to command attention. Body text remains generous in line-height (`1.5` to `1.6`) for long-form readability against dark backgrounds. Use uppercase and tracking on `mono-label` to evoke a "terminal" feel.

## Layout & Spacing
The layout follows a **Fluid Grid** model with a sidebar-main architecture. 
- **Sidebar:** Fixed width (80px collapsed / 256px expanded) with internal `md` (16px) padding.
- **Main Content:** Uses a 12-column grid for standard cards.
- **Rhythm:** A 4px base unit controls all spacing. Grids utilize a 24px (`lg`) gap to ensure elements feel distinct even with blurred backgrounds.
- **Breakpoints:** On mobile, margins reduce to 16px, and grid columns stack to a single column or 2-column flex layouts.

## Elevation & Depth
Depth is created through transparency and inner lighting rather than traditional drop shadows.
1. **The Void (Base):** Background color `#080f16`.
2. **Glass Panels:** Standard containers use `rgba(255, 255, 255, 0.03)` with a `40px` backdrop blur and a `1px` subtle white border. 
3. **Clay Surfaces:** Active elements use a slightly more opaque `rgba(255, 255, 255, 0.07)` with an inner white highlight (`inset 2px 2px 4px`) to create a "squishy" or physical feel.
4. **Glow Shadows:** High-priority cards or active buttons emit a tinted ambient glow (`0 0 15px`) using the Primary or Secondary accent colors to indicate focus.

## Shapes
The shape language is **Rounded** and friendly yet structured. Standard buttons and cards use `rounded-xl` (12px). Pill shapes (`rounded-full`) are reserved specifically for chips, tags, and small utility badges to distinguish them from actionable containers. Navigation items use a softer `rounded-xl` for a modern, comfortable feel.

## Components
- **Buttons:** Primary buttons use the "Clay Surface" style with a Cyan background and black text. Hover states should trigger a Cyan glow. Secondary buttons use the "Glass Panel" style with a light border.
- **Chips/Badges:** Small, pill-shaped glass containers with icons. Used for status and metadata.
- **Input Fields:** Darker than the background (`primary-container`), with 12px rounding and a 1px border that glows on focus.
- **Cards:** Glassmorphic containers with a 24px internal padding. They should support "Glow" states on hover or active status.
- **Sidebar Nav:** Uses an "Active Indicator" bar (4px wide, rounded) on the left side of the active item, paired with a subtle background tint.
- **Metric Displays:** Feature large display typography with gradient text effects (Cyan/Purple) and micro-sparkline visualizations.

---

## Implementation notes (v1.5.0)

How the spec maps onto Tk, which has no backdrop blur, `rgba()` or letter-spacing:

- **Glass:** panels are Pillow-rendered rounded images (3x supersampled) behind real widgets, with a 1px hairline
  border and a faint light edge along the top. Translucent fills are *pre-blended* over the surface they sit on
  (`theme.blend`). The panel fill is 4.5% white rather than 3%, because without blur a 3% panel disappears on many displays.
- **Cyan glow:** primary buttons, focused fields, toggles and the selected App Rules card get a blurred cyan halo.
- **Type:** Inter and Geist Mono are used if present in `snapui/assets/fonts/`; otherwise Segoe UI Variable / Segoe UI
  and Cascadia Mono / Consolas. Sizes are in device pixels via `dp()` so they scale with DPI. Tk offers only normal and bold,
  so 600 weight uses the "SemiBold" family when installed. Micro-labels are upper-case mono (no tracking available).
- **Warning colour:** the spec has none, so amber (`#f5c26b`) is used sparingly for warnings. Snooze uses amethyst.
- **Sidebar:** 256px, collapsing to an 80px icon rail below 1080dp window width or on request.
- **Icons:** a 24-unit stroke icon set drawn in Pillow (`snapui/icons.py`), tinted per state.
- **Accessibility:** every text/background pair is tested for WCAG AA (4.5:1) in `tests/test_theme.py`; all controls
  are reachable and operable by keyboard with a visible focus ring.
