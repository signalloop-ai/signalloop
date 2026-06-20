# Reference Solution Notes

The advanced reference solution keeps the assessment intentionally in memory while
implementing the required product behavior:

- normalized unique user emails,
- validated team membership roles and duplicate membership rejection,
- team-scoped lead permissions,
- partial update semantics using `exclude_unset=True`,
- ordered status transitions,
- archive/delete semantics with auditability,
- task event generation for create, update, status, comment, and archive,
- comment actor access validation,
- deterministic task list ordering and pagination.

The reference solution should not be exposed to candidates or the AI collaborator.
