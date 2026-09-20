# Case Management

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Requesters submit and follow cases. Agents handle queues and case activity throughout the working day. Implementers and administrators configure environments, fields, workflows and permissions.

## Product Purpose

A generic, configurable case-management product with a stable business core. Success means quickly finding, understanding and acting on cases, with configuration manageable without code changes.

## Operating Context

The active local application is http://localhost:3000/. The existing stack is React, Material UI and a Python API with persistent SQLite data. Hebrew RTL is primary; English LTR is supported.

## Capabilities and Constraints

AGENTS.md and docs/api/API_SPEC.md remain the authoritative business and API contracts. Preserve all existing actions, permissions, configuration sources, data and navigation. No demo data, new business definitions or database reset. Responsive flows must work at 360px without horizontal page scrolling. Configuration and permission controls remain explicit and actionable.

## Product Principles

- Fast everyday work and straightforward inline actions.
- Shared, consistent components across portal, workspace, cases, reports and administration.
- Server-enforced authorization and truthful feedback.
- Business values come from persisted configuration.

## Confirmed Design Scope

The user requested a redesign using Taste, Emil Kowalski and Impeccable, and confirmed that all screens must speak the same visual language. No existing visual feature was designated for preservation.

## Evidence on Hand

Existing source, localized copy, API contracts and regression suites. Production-like local data must be preserved and must not be copied into design examples or committed artifacts.
