#!/usr/bin/env python3
"""
auth0_to_rsa.py — Convert an Auth0 user export CSV into the CSV format
RSA Cloud Authentication Service expects for a Local (file-based) Identity Source.

Why this exists: Auth0's export is a generic account dump (every field Auth0
might store about a user). RSA's import template is shaped around its own
identity source schema. They were never going to line up automatically —
this script is the one-time translation step between them.

Usage:
    python3 auth0_to_rsa.py --input auth0_export.csv --output rsa_import.csv
    python3 auth0_to_rsa.py --input auth0_export.csv.gz --output rsa_import.csv

Auth0's export downloads as .csv.gz — pass it straight in, no need to gunzip
first. Plain .csv also works.

Re-run this every time you re-export from Auth0. RSA's "Local" identity
source is a manual file import, not a live sync — new Auth0 users won't
appear in RSA until you export and run this again.
"""

import argparse
import csv
import gzip
import sys

RSA_HEADER = [
    "Email", "First Name", "Last Name", "Username", "Alternate Usernames",
    "SMS Phones", "Voice Phones", "Group Membership", "User Password",
    "Password Delivery Method", "Initial Password Delivery Location", "Manager's Email",
]


def clean(value):
    """Auth0's export prefixes quoted text fields with a stray leading
    apostrophe (an Excel artifact that forces text formatting). Strip it if
    present; harmless no-op if the export doesn't have it."""
    return value.lstrip("'").strip() if value else ""


def convert_row(row, username_field):
    email = clean(row.get("email"))
    if not email:
        return None

    given = clean(row.get("given_name"))
    family = clean(row.get("family_name"))
    nickname = clean(row.get("nickname"))

    if username_field == "email":
        username = email
    else:
        username = clean(row.get(username_field)) or email

    return {
        "Email": email,
        # given_name is often empty for self-signup users with no profile
        # fields collected — fall back to nickname, then the email's local
        # part, so First Name (a required RSA field) is never blank.
        "First Name": given or nickname or email.split("@")[0],
        "Last Name": family,  # optional in RSA's template — blank is fine
        "Username": username,
        "Alternate Usernames": "",
        "SMS Phones": "",
        "Voice Phones": "",
        "Group Membership": "",
        # RSA isn't handling primary auth here (Auth0 is) — nothing to set.
        "User Password": "",
        "Password Delivery Method": "",
        "Initial Password Delivery Location": "",
        "Manager's Email": "",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input", "-i", required=True, help="Auth0 user export CSV (.csv or .csv.gz)")
    parser.add_argument("--output", "-o", default="rsa_user_import.csv", help="Output CSV for RSA import (default: rsa_user_import.csv)")
    parser.add_argument(
        "--username-field",
        default="email",
        help=(
            "Auth0 column to use as RSA's Username. Default is 'email', which "
            "MUST match whatever identifier your Auth0 Action sends to your "
            "step-up service (e.g. event.user.email) — otherwise RSA can't "
            "look up the right user at authentication time. Only override "
            "this if your Action identifies users a different way."
        ),
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Print per-row skip/duplicate warnings")
    args = parser.parse_args()

    opener = gzip.open if args.input.endswith(".gz") else open

    try:
        with opener(args.input, mode="rt", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            if "email" not in reader.fieldnames:
                print(f"error: '{args.input}' has no 'email' column — is this an Auth0 user export?", file=sys.stderr)
                sys.exit(1)
            rows_in = list(reader)
    except FileNotFoundError:
        print(f"error: input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    seen_emails = set()
    rows_out = []
    skipped = 0
    duplicates = 0

    for row in rows_in:
        converted = convert_row(row, args.username_field)
        if converted is None:
            skipped += 1
            if args.verbose:
                print(f"skipped row with no email: {row}", file=sys.stderr)
            continue
        if converted["Email"] in seen_emails:
            duplicates += 1
            if args.verbose:
                print(f"duplicate email, keeping first occurrence: {converted['Email']}", file=sys.stderr)
            continue
        seen_emails.add(converted["Email"])
        rows_out.append(converted)

    with open(args.output, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=RSA_HEADER)
        writer.writeheader()
        writer.writerows(rows_out)

    print(f"Wrote {len(rows_out)} user(s) to {args.output}")
    if skipped:
        print(f"Skipped {skipped} row(s) with no email (use -v for details)")
    if duplicates:
        print(f"Skipped {duplicates} duplicate email(s) (use -v for details)")


if __name__ == "__main__":
    main()
