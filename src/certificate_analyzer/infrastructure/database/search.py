"""Unicode-aware substring search for SQLite connections."""

from sqlalchemy import func, or_


def casefold_contains(session, columns, search):
    """Build a literal, case-insensitive condition for Russian text."""
    connection = session.connection().connection.driver_connection
    connection.create_function(
        "ca_casefold", 1, lambda value: (value or "").casefold(), deterministic=True
    )
    term = search.strip().casefold()
    return or_(*(func.ca_casefold(column).contains(term, autoescape=True) for column in columns))
