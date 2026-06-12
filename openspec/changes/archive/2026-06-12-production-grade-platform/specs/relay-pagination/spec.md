## ADDED Requirements

### Requirement: Node interface and global object identification

FastQL SHALL provide a Relay `Node` interface with a non-null `id: ID!` field and
a root `node(id: ID!): Node` query that resolves any object by its global ID. The
framework SHALL encode/decode global IDs combining the type name and an inner id.

#### Scenario: Object resolved by global id

- **WHEN** a client queries `node(id: <globalId>)` for an object implementing `Node`
- **THEN** the correct object is resolved and its concrete `__typename` is reported

#### Scenario: Global id round-trips

- **WHEN** a type name and inner id are encoded into a global id and later decoded
- **THEN** the original type name and inner id are recovered

### Requirement: Connection, Edge, and PageInfo types

FastQL SHALL provide generic `Connection[T]`, `Edge[T]`, and `PageInfo` types
conforming to the Relay Cursor Connections specification, including `edges`,
`pageInfo`, `node`, `cursor`, `hasNextPage`, `hasPreviousPage`, `startCursor`,
and `endCursor`.

#### Scenario: Connection field exposes Relay shape

- **WHEN** a field returns `Connection[User]`
- **THEN** the schema exposes `UserConnection` with `edges { node cursor }` and `pageInfo { hasNextPage hasPreviousPage startCursor endCursor }`

### Requirement: Cursor pagination arguments and slicing

Relay connection fields SHALL accept `first`/`after` and `last`/`before`
arguments and a pagination helper SHALL slice an ordered dataset accordingly,
populating cursors and page-info flags.

#### Scenario: Forward pagination

- **WHEN** a connection is queried with `first: 2, after: <cursor>`
- **THEN** at most two edges following the cursor are returned with `hasNextPage` set correctly

#### Scenario: Backward pagination

- **WHEN** a connection is queried with `last: 2, before: <cursor>`
- **THEN** at most two edges preceding the cursor are returned with `hasPreviousPage` set correctly
