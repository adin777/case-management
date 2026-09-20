---
name: Case Management
description: Light paper and blue ink for everyday case work
colors:
  primary: "#203e5b"
  primary-deep: "#152e46"
  primary-tint: "#e9eff5"
  canvas: "#f5f7f9"
  paper: "#ffffff"
  navigation: "#eef2f6"
  text: "#202d3a"
  muted: "#59697a"
  border: "#dce3eb"
  success: "#24634b"
  warning: "#8b530d"
  error: "#b3343e"
  info: "#315e85"
typography:
  headline:
    fontFamily: '"Noto Sans Hebrew", "Segoe UI", sans-serif'
    fontSize: "1.875rem"
    fontWeight: 700
    lineHeight: 1.4
    letterSpacing: "-.025em"
  title:
    fontFamily: '"Noto Sans Hebrew", "Segoe UI", sans-serif'
    fontSize: "1.0625rem"
    fontWeight: 650
    lineHeight: 1.5
  body:
    fontFamily: '"Noto Sans Hebrew", "Segoe UI", sans-serif'
    fontSize: ".9375rem"
    lineHeight: 1.65
  secondary:
    fontFamily: '"Noto Sans Hebrew", "Segoe UI", sans-serif'
    fontSize: ".8125rem"
    lineHeight: 1.6
rounded:
  control: "8px"
  panel: "12px"
  chip: "6px"
spacing:
  small: "8px"
  medium: "16px"
  large: "24px"
components:
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.paper}"
    rounded: "{rounded.control}"
    height: "44px"
  button-outlined:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.primary}"
    rounded: "{rounded.control}"
  input:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.text}"
    rounded: "{rounded.control}"
    height: "44px"
  navigation-item:
    backgroundColor: "{colors.primary-tint}"
    textColor: "{colors.primary}"
    rounded: "{rounded.control}"
  chip:
    backgroundColor: "{colors.paper}"
    rounded: "{rounded.chip}"
  panel:
    backgroundColor: "{colors.paper}"
    rounded: "{rounded.panel}"
    padding: "24px"
---

## Overview

**Creative North Star: "Ordered working files"**

Ordered working files: a stable navigation column, quiet reading surfaces and precise actions support repeated daily work. The light, ink-blue direction was selected by the user. Shared MUI components carry the same identity across the portal, workspace, reports, case details and configuration.

**Key Characteristics:**

- Blue ink for actions and selection.
- Continuous lists for case and module directories.
- Self-hosted Hebrew typography and explicit reading direction.
- Restrained interaction feedback with reduced-motion support.

## Colors

Primary blue ink marks action and selection. Cool paper distinguishes the canvas, navigation and content. Success, warning, error and information retain semantic roles rather than decorative use. Text and muted text contrast are protected by automated tests.

## Typography

Noto Sans Hebrew is self-hosted under the SIL Open Font License with font-display swap. ScreenHeader uses the headline style as an h1, reduced to 1.5rem below the medium breakpoint. Section headings use the title style. Supporting text and tables use the secondary style. Identifiers and numeric columns use tabular numerals.

## Layout

Desktop navigation occupies 248px at the reading edge. Below 900px it becomes a temporary drawer. Shared forms use one, two or four columns with minmax(0, 1fr). Panels use generous separation and tighter internal groups. Small screens reduce card padding to 16px.

The portal and module directories use continuous rows. Global-field tables become labeled stacked records below 900px, with drag and action controls beside the field name. Case details retain their own actions; the shell's floating create action is omitted on case routes. Apply this responsive record pattern when adding other comparable configuration tables.

## Elevation & Depth

Panels use borders and tonal separation. Cards have no shadow. Overlays use the shared shadow (0 12px 36px rgba(23, 42, 63, .16)); dialogs have a 16px radius. Keyboard focus uses a visible ink outline.

## Shapes

Controls, panels and chips use the frontmatter radius scale. Outlined icons come from the existing MUI library. Small rounded controls support dense work without turning every item into a pill.

## Components

Primary buttons are ink on paper's inverse, with a minimum height of 44px for large and coarse-pointer actions. Ordinary desktop buttons have a 40px minimum. Outlined actions use paper and a quiet border. Pointer press moves a button by 1px; repeated work has no entrance choreography.

Inputs have a 44px minimum height, a light outline and clear focus state. Chips preserve semantic text and color. Navigation marks the active section even on nested routes. NotificationBell is a single native keyboard-operable button. ScreenHeader presents the page title, purpose and action together.

State transitions use cubic-bezier(0.23, 1, 0.32, 1), generally 120–220ms. Reduced-motion preference removes nonessential animation and transitions. No generated decorative imagery is needed for this operating interface.

## Do's and Don'ts

- Do reuse shared tokens, headers and responsive primitives.
- Do keep business actions and database-backed labels visible.
- Do use labeled stacked records for narrow configuration tables.
- Don't restore decorative gradients or hovering cards.
- Don't use generated identifiers as the default description of a business field.
- Don't hide an existing action to make a screen simpler.
