"""
Database helpers for Smarter's MariaDB / MySQL backend.

Smarter stores emoji and other 4-byte characters in prompts, manifests and chat
history, so every table must use the ``utf8mb4`` character set. MariaDB's
``utf8`` is the 3-byte ``utf8mb3``, which rejects them with error 1366,
"Incorrect string value". Databases created by older versions of the Helm chart,
whose MariaDB server defaulted to ``utf8``, have ``utf8mb3`` tables, and
``ALTER DATABASE ... CHARACTER SET`` only changes the default for new tables.
:func:`convert_database_to_utf8mb4` converts the existing ones.
"""

from django.db import connections
from django.db.backends.utils import CursorWrapper
from pydantic import BaseModel

from smarter.lib import logging

logger = logging.getLogger(__name__)
logger_prefix = logging.formatted_text(__name__)

UTF8MB4_CHARSET = "utf8mb4"
"""The character set that every Smarter table uses."""

UTF8MB4_COLLATION = "utf8mb4_unicode_ci"
"""The collation that every Smarter table uses.

It matches the init Job's CREATE DATABASE.
"""


def _quote(name: str) -> str:
    """
    Quote a MariaDB identifier.

    :param name: a database or table name.
    :returns: the name in backticks, with any backtick doubled.
    """
    return "`" + name.replace("`", "``") + "`"


class CharacterForeignKey(BaseModel):
    """
    A foreign key on character columns, which MariaDB won't let a table conversion change.

    MariaDB refuses to change the character set of a column that a foreign key uses, with
    error 1832, even with foreign key checks disabled. Such a foreign key is dropped before
    the conversion, and added again after it, by :meth:`drop_sql` and :meth:`add_sql`.
    """

    name: str
    table: str
    columns: list[str]
    referenced_table: str
    referenced_columns: list[str]
    update_rule: str
    delete_rule: str

    def drop_sql(self) -> str:
        """:returns: the ALTER TABLE statement that drops the foreign key."""
        return f"ALTER TABLE {_quote(self.table)} DROP FOREIGN KEY {_quote(self.name)}"

    def add_sql(self) -> str:
        """:returns: the ALTER TABLE statement that adds the foreign key again, as it was."""
        columns = ", ".join(_quote(column) for column in self.columns)
        referenced_columns = ", ".join(_quote(column) for column in self.referenced_columns)
        return (
            f"ALTER TABLE {_quote(self.table)} ADD CONSTRAINT {_quote(self.name)} FOREIGN KEY ({columns}) "
            f"REFERENCES {_quote(self.referenced_table)} ({referenced_columns}) "
            f"ON UPDATE {self.update_rule} ON DELETE {self.delete_rule}"
        )


def _character_foreign_keys(cursor: CursorWrapper, tables: list[str]) -> list[CharacterForeignKey]:
    """
    List the foreign keys on character columns, from or to any of the tables.

    :param cursor: a cursor of the database.
    :param tables: the tables that are about to be converted.
    :returns: the foreign keys, in the order of their tables and names.
    """
    cursor.execute("""
        SELECT k.TABLE_NAME, k.CONSTRAINT_NAME, k.COLUMN_NAME, k.REFERENCED_TABLE_NAME,
               k.REFERENCED_COLUMN_NAME, r.UPDATE_RULE, r.DELETE_RULE, c.CHARACTER_SET_NAME
        FROM information_schema.KEY_COLUMN_USAGE k
        JOIN information_schema.REFERENTIAL_CONSTRAINTS r
          ON r.CONSTRAINT_SCHEMA = k.CONSTRAINT_SCHEMA AND r.TABLE_NAME = k.TABLE_NAME
          AND r.CONSTRAINT_NAME = k.CONSTRAINT_NAME
        JOIN information_schema.COLUMNS c
          ON c.TABLE_SCHEMA = k.TABLE_SCHEMA AND c.TABLE_NAME = k.TABLE_NAME AND c.COLUMN_NAME = k.COLUMN_NAME
        WHERE k.TABLE_SCHEMA = DATABASE() AND k.REFERENCED_TABLE_NAME IS NOT NULL
        ORDER BY k.TABLE_NAME, k.CONSTRAINT_NAME, k.ORDINAL_POSITION
        """)
    converting = set(tables)
    foreign_keys: dict[tuple[str, str], CharacterForeignKey] = {}
    is_character: dict[tuple[str, str], bool] = {}
    for (
        table,
        name,
        column,
        referenced_table,
        referenced_column,
        update_rule,
        delete_rule,
        charset,
    ) in cursor.fetchall():
        if table not in converting and referenced_table not in converting:
            continue
        key = (table, name)
        if key not in foreign_keys:
            foreign_keys[key] = CharacterForeignKey(
                name=name,
                table=table,
                columns=[],
                referenced_table=referenced_table,
                referenced_columns=[],
                update_rule=update_rule,
                delete_rule=delete_rule,
            )
        foreign_keys[key].columns.append(column)
        foreign_keys[key].referenced_columns.append(referenced_column)
        is_character[key] = is_character.get(key, False) or charset is not None
    return [foreign_key for key, foreign_key in foreign_keys.items() if is_character[key]]


def tables_not_utf8mb4(using: str = "default") -> list[str]:
    """
    List the tables whose default character set, or any of whose columns, is not utf8mb4.

    :param using: the Django database alias.
    :returns: the table names, sorted. Empty for a database backend other than MySQL / MariaDB.
    """
    connection = connections[using]
    if connection.vendor != "mysql":
        return []
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT t.TABLE_NAME FROM information_schema.TABLES t
            WHERE t.TABLE_SCHEMA = DATABASE() AND t.TABLE_TYPE = 'BASE TABLE'
              AND t.TABLE_COLLATION NOT LIKE %s
            UNION
            SELECT c.TABLE_NAME FROM information_schema.COLUMNS c
            JOIN information_schema.TABLES t
              ON t.TABLE_SCHEMA = c.TABLE_SCHEMA AND t.TABLE_NAME = c.TABLE_NAME
            WHERE c.TABLE_SCHEMA = DATABASE() AND t.TABLE_TYPE = 'BASE TABLE'
              AND c.CHARACTER_SET_NAME IS NOT NULL AND c.CHARACTER_SET_NAME <> %s
            """,
            [f"{UTF8MB4_CHARSET}%", UTF8MB4_CHARSET],
        )
        return sorted(row[0] for row in cursor.fetchall())


def convert_database_to_utf8mb4(using: str = "default", dry_run: bool = False) -> list[str]:
    """
    Convert the database's default character set, and every table that is not utf8mb4, to utf8mb4.

    It is idempotent: a database that is already utf8mb4 is left as it is. Foreign key
    checks are disabled during the conversion, because a foreign key between two
    character columns is briefly between two character sets. MariaDB won't convert a
    column that such a foreign key uses, so these foreign keys are dropped first, and
    added again afterwards. One that can't be added again is logged, with its statement.

    :param using: the Django database alias.
    :param dry_run: if True, only report the tables that would be converted.
    :returns: the names of the tables that were converted, or would be with ``dry_run``.
    """
    connection = connections[using]
    if connection.vendor != "mysql":
        logger.info(
            "%s.convert_database_to_utf8mb4() skipped: database vendor is %s.", logger_prefix, connection.vendor
        )
        return []
    tables = tables_not_utf8mb4(using=using)
    if dry_run:
        return tables
    with connection.cursor() as cursor:
        cursor.execute("SELECT DATABASE()")
        database = cursor.fetchone()[0]
        cursor.execute(f"ALTER DATABASE {_quote(database)} CHARACTER SET {UTF8MB4_CHARSET} COLLATE {UTF8MB4_COLLATION}")
        if not tables:
            return []
        foreign_keys = _character_foreign_keys(cursor, tables)
        cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
        dropped: list[CharacterForeignKey] = []
        try:
            for foreign_key in foreign_keys:
                logger.info(
                    "%s.convert_database_to_utf8mb4() dropping foreign key: %s", logger_prefix, foreign_key.drop_sql()
                )
                cursor.execute(foreign_key.drop_sql())
                dropped.append(foreign_key)
            for table in tables:
                logger.info(
                    "%s.convert_database_to_utf8mb4() converting table %s to %s.",
                    logger_prefix,
                    table,
                    UTF8MB4_CHARSET,
                )
                cursor.execute(
                    f"ALTER TABLE {_quote(table)} CONVERT TO CHARACTER SET {UTF8MB4_CHARSET} COLLATE {UTF8MB4_COLLATION}"
                )
        finally:
            for foreign_key in dropped:
                try:
                    cursor.execute(foreign_key.add_sql())
                # pylint: disable=broad-except
                except Exception as e:
                    logger.error(
                        "%s.convert_database_to_utf8mb4() could not add foreign key %s again: %s. Add it with: %s",
                        logger_prefix,
                        foreign_key.name,
                        e,
                        foreign_key.add_sql(),
                    )
            cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
    return tables
