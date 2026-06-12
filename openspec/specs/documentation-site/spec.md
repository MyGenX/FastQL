# Documentation Site Specification

## Purpose

Define the repository-local FastQL documentation experience, its content accuracy,
quality controls, and readiness for future hosted deployment.

## Requirements

### Requirement: Repository-local documentation project
The repository SHALL contain a Mintlify documentation project under `docs/` with a valid `docs.json`, MDX content, scoped assets and styling, and documentation-only tooling that does not alter FastQL's Python runtime dependencies.

#### Scenario: Documentation project is self-contained
- **WHEN** a contributor inspects the `docs/` directory
- **THEN** it contains the configuration, navigation content, assets, and commands required to preview and validate the site

### Requirement: Product landing page
The documentation SHALL provide a responsive custom landing page whose first viewport identifies FastQL, explains its code-first GraphQL value, and exposes clear installation and quickstart actions. The page SHALL use real FastQL product imagery and SHALL provide visible continuation into project capabilities.

#### Scenario: Evaluator opens the documentation root
- **WHEN** a visitor opens the documentation home page on desktop or mobile
- **THEN** FastQL, its primary value, installation path, quickstart path, and a hint of subsequent content are visible without overlapping or clipped content

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

### Requirement: Documentation accuracy and source-of-truth policy
User-facing examples SHALL match the current public FastQL API, and normative product behavior SHALL remain sourced from OpenSpec. Documentation SHALL label maturity and unsupported features accurately and SHALL link specification summaries to canonical capability files.

#### Scenario: Quickstart example remains executable
- **WHEN** documentation validation runs
- **THEN** the canonical quickstart or its shared example is exercised against the installed FastQL package without errors

#### Scenario: Specification content is traceable
- **WHEN** a reader opens the specification catalog
- **THEN** each documented capability links to an existing canonical OpenSpec specification

### Requirement: Local preview and quality validation
The documentation project SHALL document Node.js 20.17+ and provide commands for local preview, strict Mintlify validation, broken-link checking including anchors, accessibility checks, and a combined quality check.

#### Scenario: Contributor validates documentation
- **WHEN** a contributor runs the documented combined check from `docs/`
- **THEN** configuration, page build, internal links, anchors, and accessibility are checked before review

### Requirement: Deployment-ready repository configuration
The documentation source SHALL be suitable for a future Mintlify GitHub connection using `docs/` as the repository subdirectory, while requiring no account credentials or hosted deployment to complete this change.

#### Scenario: Deployment owner connects Mintlify later
- **WHEN** an administrator configures Mintlify to build the repository's `docs/` subdirectory
- **THEN** the committed documentation source can deploy without restructuring its content

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
