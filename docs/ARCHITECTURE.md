# Architecture

## Design summary

The filesystem is the transport and audit surface. Small scripts provide claiming, validation, watching, and digest behavior while keeping the task card human-readable.

## Main components

- Write a task card to inbox
- Claim it into processing
- Produce artifacts and evidence
- Move to processed, failed, or awaiting approval
- Publish a digest or outbox message

## Initial implementation boundary

Start with a local, inspectable implementation. Prefer plain files, small typed schemas, and deterministic commands before introducing a database, hosted service, or provider-specific adapter.

## Verification

Every MVP feature should have at least one fixture, one failure case, and one visible verification artifact. Keep inferred behavior separate from measured behavior.
