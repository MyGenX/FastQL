# Documentation Site — Delta

## MODIFIED Requirements

### Requirement: Task-oriented documentation navigation
The documentation SHALL organize pages into getting started, schema authoring, data resolution, data and performance, protocol features, federation, integrations, operations, tooling, reference, architecture, specifications, and contribution areas, with every configured navigation entry resolving to an MDX page. No navigation group SHALL mix unrelated themes the way a catch-all "advanced" area does, and page URLs SHALL reflect their navigation area, with redirects preserving previously published URLs.

#### Scenario: New user follows the learning path
- **WHEN** a new user navigates from introduction through quickstart and first schema
- **THEN** the pages provide an ordered path from installation to executing and serving a working FastQL schema

#### Scenario: Contributor finds internals
- **WHEN** a contributor needs the parser, type-system, validation, or execution design
- **THEN** the architecture and specification navigation exposes the relevant technical content and canonical source links

#### Scenario: Reader locates a capability by theme
- **WHEN** a reader looks for data loading, streaming protocol features, federation, or operational guidance
- **THEN** each topic is found in a navigation group dedicated to that theme rather than a general advanced section

#### Scenario: Previously published URL is requested
- **WHEN** a visitor opens a page URL that existed before the regrouping
- **THEN** the site redirects to the page's current location

## ADDED Requirements

### Requirement: Ecosystem-standard topic coverage
The documentation SHALL provide dedicated pages for FAQ, authentication patterns, deployment guidance, lazy (forward-reference) type definitions, and a federation section covering setup, entity resolution, and custom federation directives. Authentication and deployment pages SHALL present integration patterns that respect the framework-agnostic core boundary rather than documenting nonexistent built-ins.

#### Scenario: Reader needs an ecosystem-standard topic
- **WHEN** a reader searches the navigation for FAQ, authentication, deployment, or lazy types
- **THEN** a dedicated page exists and reflects current FastQL behavior

#### Scenario: Federation reader goes beyond setup
- **WHEN** a reader has completed federation setup and needs entity resolution or custom federation directives
- **THEN** dedicated federation pages cover those topics

### Requirement: Public documentation roadmap
The project status page SHALL contain a planned-topics section listing documentation deferred until its feature or policy exists, including at minimum schema/query codegen, editor and type-checker integration guidance, and upgrading/breaking-changes documentation.

#### Scenario: Reader checks what is coming
- **WHEN** a reader opens the project status page
- **THEN** a planned section distinguishes deferred documentation topics from implemented capabilities and current boundaries
