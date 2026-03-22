# Folded Decomposition Follow-ups

This note tracks follow-up work intentionally out of scope for the 2D MVP.

## Priority Follow-ups

1. 3D folded decomposition for curved polyhedra.
2. Singular and near-singular kernel quadrature extensions.
3. Downstream adapter into `volumential` rule-consumption paths.

## CAD Core

OpenCascade is now the designated CAD core for exact 2D Section 6 clipping
workflows. Remaining follow-ups focus on extending that CAD-native path to
broader geometry classes and 3D.

## Rationale

The MVP establishes a deterministic and testable 2D folded core first.
The follow-ups above extend representation coverage and solver-facing accuracy
without blocking the initial architecture-aligned implementation.
