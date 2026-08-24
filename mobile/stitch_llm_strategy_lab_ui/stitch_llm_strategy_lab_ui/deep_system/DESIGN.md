---
name: Deep System
colors:
  surface: '#10131a'
  surface-dim: '#10131a'
  surface-bright: '#363941'
  surface-container-lowest: '#0b0e15'
  surface-container-low: '#191b23'
  surface-container: '#1d2027'
  surface-container-high: '#272a31'
  surface-container-highest: '#32353c'
  on-surface: '#e1e2ec'
  on-surface-variant: '#c2c6d6'
  inverse-surface: '#e1e2ec'
  inverse-on-surface: '#2e3038'
  outline: '#8c909f'
  outline-variant: '#424754'
  surface-tint: '#adc6ff'
  primary: '#adc6ff'
  on-primary: '#002e6a'
  primary-container: '#4d8eff'
  on-primary-container: '#00285d'
  inverse-primary: '#005ac2'
  secondary: '#4cd7f6'
  on-secondary: '#003640'
  secondary-container: '#03b5d3'
  on-secondary-container: '#00424e'
  tertiary: '#ffb786'
  on-tertiary: '#502400'
  tertiary-container: '#df7412'
  on-tertiary-container: '#461f00'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#d8e2ff'
  primary-fixed-dim: '#adc6ff'
  on-primary-fixed: '#001a42'
  on-primary-fixed-variant: '#004395'
  secondary-fixed: '#acedff'
  secondary-fixed-dim: '#4cd7f6'
  on-secondary-fixed: '#001f26'
  on-secondary-fixed-variant: '#004e5c'
  tertiary-fixed: '#ffdcc6'
  tertiary-fixed-dim: '#ffb786'
  on-tertiary-fixed: '#311400'
  on-tertiary-fixed-variant: '#723600'
  background: '#10131a'
  on-background: '#e1e2ec'
  surface-variant: '#32353c'
typography:
  display-lg:
    fontFamily: Inter
    fontSize: 40px
    fontWeight: '700'
    lineHeight: 48px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Inter
    fontSize: 32px
    fontWeight: '600'
    lineHeight: 40px
    letterSpacing: -0.01em
  headline-lg-mobile:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
  title-md:
    fontFamily: Inter
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
  body-lg:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  body-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  label-md:
    fontFamily: Geist
    fontSize: 12px
    fontWeight: '500'
    lineHeight: 16px
    letterSpacing: 0.05em
  code-sm:
    fontFamily: Geist
    fontSize: 13px
    fontWeight: '400'
    lineHeight: 18px
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  page-margin: 1rem
  gutter: 1rem
  stack-sm: 0.5rem
  stack-md: 1rem
  stack-lg: 1.5rem
  component-padding-x: 1rem
  component-padding-y: 0.75rem
---

## Brand & Style

The design system is engineered for high-stakes fintech and developer utility. It balances the precision of a code editor with the premium density of a modern financial terminal. The aesthetic is a refined **Minimalist-Corporate** hybrid, prioritizing legibility and structural clarity over decorative elements. 

The user should feel a sense of absolute control and stability. By using a "Deep Dark" foundation, we reduce visual fatigue for long-session power users while allowing critical data points (profit/loss, execution states) to command attention through high-contrast accents. The style avoids "gamer" tropes, opting instead for a technical, systematic elegance that suggests institutional-grade reliability.

## Colors

This design system utilizes a layered dark palette to establish depth without relying on heavy shadows. 

- **Primary & Secondary:** Used exclusively for high-priority actions, active states, and brand-critical identifiers. 
- **The Surface Hierarchy:** The primary background (`#0B0E14`) acts as the "ground." Elements placed on top use the Surface (`#161B22`) color to indicate interaction potential or content grouping.
- **Semantic Colors:** Success, Error, and Warning colors are optimized for visibility against dark backgrounds, ensuring critical financial status or system errors are never missed.
- **Borders:** Thin 1px borders (`#30363D`) are the primary method for defining element boundaries, creating a crisp, technical feel.

## Typography

The typography strategy employs **Inter** for core interface elements due to its exceptional legibility and neutral character. **Geist** is introduced for labels and monospaced data, providing a subtle "developer" aesthetic for technical strings, ID numbers, and currency values.

- **Scale:** We strictly avoid text smaller than 12px to ensure accessibility on mobile displays.
- **Hierarchy:** High-level headers use tight letter spacing and bold weights to feel substantial. Body text maintains a generous line height (1.5x) to ensure readability in data-dense layouts.
- **Monospace Usage:** Use the `label` and `code` roles for any numeric data that updates frequently (e.g., stock tickers, balances) to prevent layout "shimmer" as digits change.

## Layout & Spacing

This design system uses a **Fluid Column Grid** model for mobile, centered around a 16px (1rem) base unit.

- **Grid:** On mobile, use a 4-column structure with 16px margins and 16px gutters.
- **Touch Targets:** All interactive elements (buttons, list items, toggles) must maintain a minimum height of 48px to satisfy ergonomic requirements.
- **Consistency:** Spacing between related items in a card (e.g., a label and its value) should be 8px (`stack-sm`), while spacing between distinct sections or cards should be 16px or 24px.
- **Safe Areas:** Adhere strictly to mobile device safe areas, ensuring the bottom navigation or home indicators do not overlap with primary actions.

## Elevation & Depth

In this system, depth is communicated through **Tonal Layering** and **Subtle Outlines** rather than traditional shadows.

1.  **Level 0 (Base):** The darkest layer (`#0B0E14`), used for the background of the entire app.
2.  **Level 1 (Surface):** Elevated cards and containers (`#161B22`). These should have a 1px border (`#30363D`) to distinguish them from the background.
3.  **Level 2 (Overlay):** Modals, bottom sheets, and menus. These use a slightly lighter surface color or a very subtle 10% white tint over the surface color, paired with a 24px blur background overlay for the content beneath.

Avoid using drop shadows unless the element is floating (e.g., a Floating Action Button). In those cases, use a sharp, 4px offset shadow with 20% opacity black.

## Shapes

The shape language is professional and modern, using **Rounded** corners to soften the technical nature of the UI.

- **Primary Containers:** Cards, input fields, and large buttons use a 12px or 16px (`rounded-lg`) radius.
- **Small Elements:** Chips, checkboxes, and tags use a smaller 4px or 8px radius.
- **Consistency:** Never mix sharp corners with rounded ones within the same component hierarchy. A card with a 16px radius should contain buttons with a consistent 8-12px radius.

## Components

- **Buttons:** 
  - *Primary:* Solid Primary Blue (`#3B82F6`) with White text. High-contrast.
  - *Secondary:* Outlined with a 1px border (`#30363D`). No fill.
  - *Tertiary:* Ghost style, text only, for low-priority actions.
- **Input Fields:** Background should be `#161B22` with a 1px border. On focus, the border transitions to the Primary Blue with a subtle 2px outer glow.
- **Cards:** Use the `#161B22` surface color. Ensure a consistent 16px internal padding for all content.
- **Chips/Tags:** Used for statuses (e.g., "Pending", "Completed"). Use low-opacity fills of the semantic colors (e.g., Success green at 15% opacity) with high-saturation text of the same color.
- **Data Rows:** List items should have a 48px-56px height, with a 1px bottom separator (`#30363D`) that stops 16px from the edge of the screen.
- **Status Indicators:** Use small 8px circles for "Live" or "System Status" indicators, utilizing the semantic palette for instant recognition.