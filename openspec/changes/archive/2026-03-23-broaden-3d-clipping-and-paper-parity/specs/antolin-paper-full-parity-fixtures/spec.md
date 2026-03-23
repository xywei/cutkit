## ADDED Requirements

### Requirement: Antolin-paper fixture matrix includes full-scope entries
The parity fixture set SHALL include antolin-paper full-scope fixtures for both
polygonized and CAD-native geometry modes.

#### Scenario: Polygonized antolin-paper full fixture is present
- **WHEN** fixture presence tests run
- **THEN** `antolin-paper-polygonized-full.json` exists and is included in the
  documented fixture matrix

#### Scenario: CAD-native antolin-paper full fixture remains comparable in
unavailable environments
- **WHEN** CAD is unavailable in the current environment
- **THEN** `antolin-paper-cad-native-full.json` remains valid as a placeholder
  baseline with explicit skip semantics
