# ETL status

The canonical loader is [`scripts/build_warehouse.py`](../scripts/build_warehouse.py). It preserves the nine CSV source contracts in the `raw` schema, checks logical row counts, and runs the staging and analytics SQL. See [setup](../docs/setup.md).

The Python package in this directory is a provisional alternative built against `sql/01_raw_schema.sql`; its raw table names, columns, and transformations differ from the canonical `database/` warehouse contract. Do not use `python -m etl.pipeline` to populate the canonical warehouse without first reconciling and testing those contracts.
