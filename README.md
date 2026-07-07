# auth0-to-rsa-import

Converts an Auth0 user export CSV into the CSV format RSA Cloud Authentication
Service expects for a **Local (file-based) Identity Source**.

## Why this exists

Auth0's export is a generic account dump — every field Auth0 might store
about a user. RSA's import template is shaped around its own identity source
schema. The two were never going to line up automatically; this script is
the one-time translation step between them.

## Usage

```bash
python3 auth0_to_rsa.py --input auth0_export.csv.gz --output rsa_user_import.csv
```

Auth0's export downloads as `.csv.gz` — pass it straight in, no need to
gunzip first. Plain `.csv` also works.

No dependencies beyond the Python standard library — nothing to `pip install`.

Options:

| Flag | Default | Description |
|---|---|---|
| `--input`, `-i` | *(required)* | Auth0 user export, `.csv` or `.csv.gz` |
| `--output`, `-o` | `rsa_user_import.csv` | Output path |
| `--username-field` | `email` | Auth0 column to use as RSA's `Username` — see below |
| `--verbose`, `-v` | off | Print each skipped/duplicate row |

## Username field

RSA's `Username` needs to match whatever your Auth0 Action sends to the
step-up service — usually `event.user.email`. If it doesn't match, imports
still succeed but real-time lookups against RSA fail at auth time. Default
is `email`; only change `--username-field` if your Action identifies users
some other way.

## What gets mapped

| RSA field | Source |
|---|---|
| Email | Auth0 `email` |
| First Name | Auth0 `given_name`, falling back to `nickname`, then the email's local part (self-signup test users often have no profile fields set — this guarantees the required field is never blank) |
| Last Name | Auth0 `family_name` (optional in RSA's template — blank is fine) |
| Username | Auth0 `email` by default (see above) |
| Everything else (phones, groups, password, manager) | Left blank — not applicable here since Auth0 handles primary auth and RSA only ever validates the second-factor code |

Rows with no email are skipped. Duplicate emails keep the first occurrence
and skip the rest. Use `-v` to see exactly what was skipped and why.

## This is a snapshot import, not a live sync

RSA's "Local" identity source is manual, file-based import — not directory
sync. New users created in Auth0 after you last ran this script will not
appear in RSA automatically. Re-export from Auth0 and re-run this script
whenever your user list changes.

## Context

Built for an Auth0 → RSA SecurID hardware TOTP MFA integration where:
- All authentication is ROPC (no Universal Login, no redirects to any
  page not controlled by the relying party)
- Auth0 is the sole identity provider (no separately hosted user database)
- RSA validates the second factor via an external step-up service, not
  through Auth0's native MFA

## License

MIT — see LICENSE.
