"""
Boundary validation for caller-supplied identifiers.

postgrest-py does not escape filter *values*. Reading the installed client:

  * ``filter(column, op, criteria)`` calls ``sanitize_param`` on the column
    only -- ``criteria`` is concatenated raw, so ``.eq()`` values are raw.
  * ``or_(filters)`` sanitizes ``reference_table`` and interpolates
    ``filters`` verbatim. An f-string here is string-built query language.
  * ``in_()`` does map ``sanitize_param`` over its values, but that helper
    only wraps a value in double quotes when it contains one of ``,:()``
    and never escapes a quote already inside it.

So any caller-controlled value reaching a query is part of the query. The
defence is to refuse anything that is not the shape we expect, at the edge:
a string that parses as a UUID cannot contain a PostgREST metacharacter,
which removes the class rather than escaping around it.

Path parameters should be annotated ``UUID`` directly -- FastAPI validates
and returns 422 for free, and the OpenAPI schema documents it. This helper
is for ids pulled out of ``body: dict`` routes, where nothing validates.
"""

from uuid import UUID

from fastapi import HTTPException, status


def uuid_field(value: object, field: str) -> str:
    """Return ``value`` as a canonical UUID string, or raise 422.

    Used for ids read out of an untyped request body. The canonical form is
    what goes to the database, so mixed case or a braced form normalises
    rather than being rejected.
    """
    try:
        return str(UUID(str(value).strip()))
    except (ValueError, AttributeError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"{field} must be a valid student id.",
        ) from None


def either_direction(query, col_a: str, col_b: str, first: str, second: str):
    """Filter a two-party table to the one row joining ``first`` and ``second``.

    Replaces the ``or_(and(a.eq.X,b.eq.Y),and(a.eq.Y,b.eq.X))`` string that
    used to be built by f-string. Both of ``friendships``, ``teamup_interest``
    and ``blocks`` carry a ``check (col_a <> col_b)`` constraint, so the
    self-pairs (X,X) and (Y,Y) cannot exist -- which makes membership of the
    two-element set exactly equivalent to the OR of the two ordered pairs,
    with no query language built from values.
    """
    pair = [first, second]
    return query.in_(col_a, pair).in_(col_b, pair)
