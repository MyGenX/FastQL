## ADDED Requirements

### Requirement: Execute normalized field hooks
Execution SHALL invoke field permissions and extensions around the normalized resolver while retaining existing sync/async interoperability, errors, and null propagation.

#### Scenario: Async extension and sync resolver
- **WHEN** an asynchronous extension wraps a synchronous resolver
- **THEN** both complete successfully and the field result is completed normally
