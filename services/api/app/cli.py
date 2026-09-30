"""
Operator commands.

    python -m app.cli create-owner --company "Acme" --email ops@acme.com --name "Ops"

Prompts for the password (never pass it on the command line: shell history).
Use this to bootstrap a workspace when self sign-up is disabled.
"""

import argparse
import asyncio
import getpass
import sys

from app.db.session import dispose_engine, get_sessionmaker
from app.services.auth_service import AuthError, signup


async def _create_owner(company: str, email: str, name: str, password: str) -> None:
    async with get_sessionmaker()() as db:
        user = await signup(
            db, company_name=company, full_name=name, email=email, password=password, ip="cli"
        )
        await db.commit()
        print(f"Created owner {user.email} in new workspace '{company}'.")
    await dispose_engine()


def main() -> None:
    parser = argparse.ArgumentParser(prog="app.cli")
    sub = parser.add_subparsers(dest="command", required=True)
    owner = sub.add_parser("create-owner", help="Create a workspace and its first owner")
    owner.add_argument("--company", required=True)
    owner.add_argument("--email", required=True)
    owner.add_argument("--name", required=True)
    args = parser.parse_args()

    password = getpass.getpass("Password: ")
    if password != getpass.getpass("Confirm password: "):
        sys.exit("Passwords do not match.")
    try:
        asyncio.run(_create_owner(args.company, args.email, args.name, password))
    except AuthError as err:
        sys.exit(err.message)


if __name__ == "__main__":
    main()
