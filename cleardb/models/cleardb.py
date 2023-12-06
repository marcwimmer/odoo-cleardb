import arrow
import psycopg2
from odoo import tools
import os
from odoo import _, api, fields, models, SUPERUSER_ID
from odoo.exceptions import UserError, RedirectWarning, ValidationError
import logging
from odoo.tools.sql import table_exists
from odoo.tools import config
from odoo.modules import load_information_from_description_file
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from contextlib import closing

logger = logging.getLogger(__name__)


class JustDelete(Exception):
    pass


class ClearDB(models.AbstractModel):
    _name = "frameworktools.cleardb"

    _complete_clear = [
        "queue.job",
        "mail.followers",
        "mail_followers_mail_message_subtype_rel",
        "bus.bus",
        "auditlog.log",
        "auditlog.log.line",
        "mail_message",
        "ir_attachment",
    ]

    @api.model
    def _run(self):
        if os.environ["DEVMODE"] != "1":
            logger.error("Anonymization needs environment DEVMODE set.")
            return

        self.show_sizes()
        # self._clear_constraint()
        #self._clear_tables()
        self._clear_custom_functions()
        self._clear_fields()

        self.show_sizes()

    def _sql_params(self):
        def wrap(x):
            return f"'{x}'"

        data = {
            "ONE_YEAR_AGO": arrow.get()
            .shift(years=-1)
            .strftime(DEFAULT_SERVER_DATETIME_FORMAT),
            "ONE_MONTH_AGO": arrow.get()
            .shift(months=-1)
            .strftime(DEFAULT_SERVER_DATETIME_FORMAT),
            "ONE_WEEK_AGO": arrow.get()
            .shift(months=-1)
            .strftime(DEFAULT_SERVER_DATETIME_FORMAT),
        }
        data = {k: wrap(v) for k, v in data.items()}
        return data

    @api.model
    def _get_clear_tables(self):
        for model in self.env.keys():
            obj = self.env[model]
            if not hasattr(obj, "_clear_db"):
                continue

            yield obj._table, obj._clear_db
        yield from [(x, True) for x in ClearDB._complete_clear]

    @api.model
    def _get_clear_fields(self):
        yield from ClearDB._nullify_columns

        for model in self.env.keys():
            obj = self.env[model]
            for field in obj._fields:
                objfield = obj._fields[field]
                if not hasattr(objfield, "cleardb"):
                    continue

        for objfield in self.env["ir.model.fields"].search([("clear_db", "=", True)]):
            pass
        # obj = self.env.get(model.model, False)
        # if getattr(obj, 'clear_db', False):
        # yield model.model

    @api.model
    def _clear_custom_functions(self):
        for model in self.env.keys():
            obj = self.env[model]
            for att in dir(obj):
                if att.startswith("_clear_db_"):
                    logger.info(f"Executing: {att}")
                    exec(f"obj.{att}()", {'obj': obj})

    @api.model
    def _clear_tables(self):
        for table, cleardb in self._get_clear_tables():
            if not table_exists(self.env.cr, table):
                logger.info(f"Truncating: Table {table} does not exist, continuing")
                continue
            logger.info(f"Clearing table {table}")
            try:
                if isinstance(cleardb, str):
                    raise JustDelete()
                with self._cr.savepoint():
                    self.env.cr.execute(f"truncate table {table} cascade")
                    self.env.cr.execute("select count(*) from res_users;")
                    if not self.env.cr.fetchone()[0]:
                        raise JustDelete(
                            f"It is not intended that res_users is "
                            f"totally cleared. Happend with: {table}"
                        )
            except JustDelete:
                try:
                    with self._cr.savepoint(), tools.mute_logger("odoo.sql_db"):
                        where = cleardb if isinstance(cleardb, str) else "1=1"
                        for k, v in self._sql_params().items():
                            where = where.replace(k, v)
                        self.env.cr.execute(f"delete from {table} where {where}")
                except psycopg2.Error as ex:
                    raise ValidationError(f"It fails here: delete from {table}: {ex}")

            self._vacuum_table(table)

    @api.model
    def _vacuum_table(self, table):
        self.env.cr.commit()
        with closing(self.env.registry.cursor()) as cr_tmp:
            cr_tmp.autocommit(True)
            cr_tmp.execute(f"VACUUM FULL {table}")

    def _clear_fields(self):
        for table in ClearDB._nullify_columns:
            table, field = table.split(":")
            table = table.replace(".", "_")
            if not table_exists(self.env.cr, table):
                logger.info(
                    f"Nullifying column {field}: Table {table} does not exist, continuing"
                )
                continue
            logger.info(f"Clearing {field} at {table}")
            self.env.cr.execute(
                f"update {table} set {field} = null where {field} is not null; "
            )

    def _clear_constraint(self):
        for table in ClearDB._constraint_drop:
            table, constrain = table.split(":")
            table = table.replace(".", "_")
            if not table_exists(self.env.cr, table):
                logger.info(f"Table {table} does not exist, continuing")
                continue
            logger.info(f"Droping {table} constrain {constrain}")
            with self._cr.savepoint():
                self.env.cr.execute(
                    f"alter table {table} drop constraint {constrain}; "
                )

    @api.model
    def show_sizes(self):
        self.env.cr.execute(
            """
WITH RECURSIVE pg_inherit(inhrelid, inhparent) AS
    (select inhrelid, inhparent
    FROM pg_inherits
    UNION
    SELECT child.inhrelid, parent.inhparent
    FROM pg_inherit child, pg_inherits parent
    WHERE child.inhparent = parent.inhrelid),
pg_inherit_short AS (SELECT * FROM pg_inherit WHERE inhparent NOT IN (SELECT inhrelid FROM pg_inherit))
SELECT table_schema
    , TABLE_NAME
    , row_estimate
    , pg_size_pretty(total_bytes) AS total
    , pg_size_pretty(index_bytes) AS INDEX
    , pg_size_pretty(toast_bytes) AS toast
    , pg_size_pretty(table_bytes) AS TABLE
  FROM (
    SELECT *, total_bytes-index_bytes-COALESCE(toast_bytes,0) AS table_bytes
    FROM (
         SELECT c.oid
              , nspname AS table_schema
              , relname AS TABLE_NAME
              , SUM(c.reltuples) OVER (partition BY parent) AS row_estimate
              , SUM(pg_total_relation_size(c.oid)) OVER (partition BY parent) AS total_bytes
              , SUM(pg_indexes_size(c.oid)) OVER (partition BY parent) AS index_bytes
              , SUM(pg_total_relation_size(reltoastrelid)) OVER (partition BY parent) AS toast_bytes
              , parent
          FROM (
                SELECT pg_class.oid
                    , reltuples
                    , relname
                    , relnamespace
                    , pg_class.reltoastrelid
                    , COALESCE(inhparent, pg_class.oid) parent
                FROM pg_class
                    LEFT JOIN pg_inherit_short ON inhrelid = oid
                WHERE relkind IN ('r', 'p')
             ) c
             LEFT JOIN pg_namespace n ON n.oid = c.relnamespace
  ) a
  WHERE oid = parent
) a
ORDER BY total_bytes DESC;
        """
        )
        recs = self.env.cr.fetchall()[:10]
        logger.info("Table Disk Sizes")
        for line in recs:
            print(f"{line[1]}: {line[3]}")
