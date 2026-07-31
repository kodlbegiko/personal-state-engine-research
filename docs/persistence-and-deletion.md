# Persistence and Deletion

## SQLite backend

`SQLiteMemoryStore` provides the first persistent implementation. It preserves the same write-policy, version, temporal and user-isolation invariants as the in-memory store while adding a derived search index and hash-only audit events.

## Deletion sequence

```text
verify user ownership
  -> hash original content for audit
  -> replace primary content with a tombstone
  -> clear tags and project metadata
  -> remove the derived search-index row
  -> commit the transaction
  -> VACUUM file-backed databases
```

The connection enables `PRAGMA secure_delete=ON` and uses a non-WAL journal. A regression test creates a unique secret, deletes it, closes the database and confirms that the secret does not occur in the database bytes.

## What this proves

It demonstrates deletion across the implemented primary table and derived search index for this SQLite backend under the tested conditions.

## What this does not prove

It does not establish deletion from:

- filesystem or cloud backups;
- replicas or external analytics;
- embedding providers;
- operating-system snapshots;
- logs outside this process;
- a database file copied before deletion;
- storage engines other than the tested SQLite configuration.

A production deletion claim must enumerate every copy and derived artifact, then test each one independently.
