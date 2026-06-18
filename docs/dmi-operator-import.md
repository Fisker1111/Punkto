# DMI Operator Import Contract

Status: operator-only draft.

This document defines the narrow contract for injecting one curated DMI weather
station atom into Punkto. It is not a public product feature.

## Scope

The DMI integration is a Punkto operator capability:

- The operator may fetch one selected DMI station and latest observation.
- The operator may review the generated atom JSON before posting it.
- The operator may post the reviewed atom through the normal relay `POST /atom`.

Public users only see the resulting atom as imported source data. They do not
get DMI import controls, station search, station browsing, weather workflows,
settings, scheduling, or automation.

## Non-goals

- No public DMI UI.
- No import button.
- No all-station import.
- No scheduler or background worker.
- No production deployment procedure in this contract.
- No credentials, API keys, or privileged relay access.
- No invented fallback values for missing DMI fields.

## Operator command shape

The operator-side tool remains separate from deployable runtime code:

```bash
python3 tools/dmi_station_atom.py --station-id 06126
```

The command prints JSON containing:

- `source_urls`: official DMI station and observation URLs used.
- `atom`: the Punkti atom candidate.

The command does not post to a relay. A separate operator action is required to
review and submit the atom.

## Atom requirements

The generated atom must preserve:

- stable station identity in the Punkto id suffix, e.g. `dmi06126`
- station name and `stationId`
- latitude, longitude, and numeric station height
- 3D GeoHash-derived `punkto`
- DMI source attribution and CC BY 4.0 license URL
- DMI station response timestamp
- latest DMI observation feature id, timestamp, parameter, and value
- `imported: true`
- `import_source: "official_dmi_metobs"`

If a required selected-station value is missing, the tool must fail closed rather
than invent data.

## Posting contract

When the operator chooses to publish the atom, it must use the existing relay
write path:

```bash
curl -X POST "$PUNKTO_NODE_URL/atom" \
  -H 'Content-Type: application/json' \
  --data-binary @reviewed-dmi-atom.json
```

The relay response `atom_id` is the durable identity for verifying that the
public feed returns the same atom.

## Required verification

For one selected station, verify:

1. `tools/dmi_station_atom.py` emits valid JSON.
2. The emitted `atom.punkto` is valid and decodes to a cell containing the DMI
   latitude, longitude, and station height.
3. The atom contains DMI attribution, source timestamps, and at least one latest
   observation.
4. A local relay accepts the reviewed atom through `POST /atom`.
5. `/feed` or `/latest` returns the atom unchanged by `atom_id`.
6. Punkto displays it only as generic imported source data.

## Boundary review checklist

Before merging changes related to DMI import, confirm:

- DMI-specific code is limited to operator tooling or tests.
- PWA display remains generic for imported source atoms.
- No public controls or workflows were added.
- No automation, scheduling, or all-station import was added.
- `DMI_AGENT_LOG.md` records objective, evidence, decision, risks, and next step.
