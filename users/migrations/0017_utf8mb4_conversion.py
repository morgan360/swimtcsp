"""Convert the whole schema from utf8mb3 to utf8mb4.

The database was created with utf8mb3, which holds at most three bytes per
character and therefore cannot store anything outside the Basic Multilingual
Plane — emoji, most obviously. MySQL does not truncate silently under
STRICT_TRANS_TABLES; it raises, so the write fails and the customer gets a 500.

Found via the chatbot, where a reply containing 😺 produced

    (1366, "Incorrect string value: '\\xF0\\x9F\\x98\\xBA' for column 'response'")

but the chatbot is only where it happened to surface. 157 columns across 47
tables were utf8mb3, so the same failure was reachable from any free-text field
a person can type into — a swimling's name, a guardian's note, the medical box.

It lives in `users` because the migration is database-wide and has to live
somewhere; `users` holds the free text most likely to carry an emoji.

Every table is converted, not just Django's app tables. Leaving any behind would
strand it on utf8mb3_general_ci, and a join across two different collations is
an "Illegal mix of collations" error — a worse fault than the one being fixed.
The database default is changed too, so tables created later inherit utf8mb4
rather than quietly reintroducing the problem.

Safe to run here specifically because MySQL is 8.0 and every table is DYNAMIC
row format: the index prefix limit is 3072 bytes, not the old 767, and the
widest indexed column in this schema is VARCHAR(255) — 1020 bytes as utf8mb4.
Re-check that before assuming this migration is portable to another database.

Irreversible by design. Going back to utf8mb3 would fail on, or silently
mangle, any four-byte character stored in the meantime.
"""
from django.db import migrations

CHARSET = "utf8mb4"
COLLATION = "utf8mb4_unicode_ci"


def convert_to_utf8mb4(apps, schema_editor):
    connection = schema_editor.connection
    if connection.vendor != "mysql":
        # SQLite is used for the test database and is UTF-8 throughout.
        return

    with connection.cursor() as cursor:
        cursor.execute("SELECT DATABASE()")
        database = cursor.fetchone()[0]

        cursor.execute(
            f"ALTER DATABASE `{database}` "
            f"CHARACTER SET {CHARSET} COLLATE {COLLATION}"
        )

        # Read the table list up front. Converting a table while iterating a
        # cursor over information_schema is asking for trouble.
        cursor.execute(
            """
            SELECT TABLE_NAME FROM information_schema.TABLES
            WHERE TABLE_SCHEMA = %s AND TABLE_TYPE = 'BASE TABLE'
            ORDER BY TABLE_NAME
            """,
            [database],
        )
        tables = [row[0] for row in cursor.fetchall()]

        for table in tables:
            cursor.execute(
                f"ALTER TABLE `{table}` "
                f"CONVERT TO CHARACTER SET {CHARSET} COLLATE {COLLATION}"
            )


class Migration(migrations.Migration):
    # DDL in MySQL commits implicitly, so wrapping this in a transaction would
    # promise an atomicity that cannot be delivered.
    atomic = False

    dependencies = [
        ("users", "0016_swimling_medical_info"),
    ]

    operations = [
        migrations.RunPython(convert_to_utf8mb4, migrations.RunPython.noop),
    ]
