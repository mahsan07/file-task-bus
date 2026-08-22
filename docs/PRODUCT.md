# Product Definition

## One-sentence promise

A transparent file-based task queue for agents and humans working across separate tools.

## Problem

Small teams need a durable bridge between agents without introducing a database or coupling every tool to the same API.

## Solution

Use folders, task cards, watchers, and explicit lifecycle states to make work visible, portable, and easy to recover.

## Users

Solo builders and small teams coordinating local agents, scripts, and human review.

## Core workflow

- Write a task card to inbox
- Claim it into processing
- Produce artifacts and evidence
- Move to processed, failed, or awaiting approval
- Publish a digest or outbox message

## MVP acceptance criteria

- Task-card schema
- Atomic claim helper
- Folder lifecycle
- Watcher
- Digest generator
- Failure and approval lanes

## Non-goals for the first release

- No hosted multi-tenant service
- No embedded credentials or provider accounts
- No irreversible external actions without a visible approval boundary
- No claim of production readiness before tests and evidence exist
