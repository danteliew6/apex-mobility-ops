"""Direct-load fallback for the Lakebase serving tables (Delta gold -> Postgres public.*).

Use this when the managed synced-table setup (setup_synced_tables.sh) is blocked, e.g. the
caller lacks CREATE CATALOG on the metastore. It copies the same five gold tables into the
same public.* names the app reads, as a one-time snapshot (re-run to refresh).

Usage: python3 lakebase/direct_load.py --profile <p> --catalog <c> --schema <s> --warehouse <id>
Needs: databricks CLI, psql.
"""
import argparse
import csv
import io
import json
import os
import subprocess
import urllib.request

TABLES = {  # table -> primary key columns
    "gold_vehicle_predictions": ["vehicle_id"],
    "gold_zone_live": ["zone_id", "hour_of_day"],
    "gold_city_hourly": ["city", "hour_of_day"],
    "gold_trips_serving": ["trip_id"],
    "gold_demand_forecast": ["city", "forecast_ts"],
}
PG_TYPES = {
    "STRING": "text", "BYTE": "bigint", "SHORT": "bigint", "INT": "bigint", "LONG": "bigint",
    "FLOAT": "double precision", "DOUBLE": "double precision", "BOOLEAN": "boolean",
    "TIMESTAMP": "timestamptz", "TIMESTAMP_NTZ": "timestamp", "DATE": "date",
}

ap = argparse.ArgumentParser()
ap.add_argument("--profile", required=True)
ap.add_argument("--catalog", required=True)
ap.add_argument("--schema", required=True)
ap.add_argument("--warehouse", required=True)
ap.add_argument("--project", default="apex-ops-db")
ap.add_argument("--database", default="databricks_postgres")
args = ap.parse_args()


def db(*a, stdin=None):
    out = subprocess.run(["databricks", "-p", args.profile, *a], capture_output=True, text=True, input=stdin)
    if out.returncode:
        raise SystemExit(out.stderr[-800:])
    return out.stdout


ep = f"projects/{args.project}/branches/production/endpoints/primary"
host = json.loads(db("postgres", "get-endpoint", ep, "-o", "json"))["status"]["hosts"]["host"]
token = json.loads(db("postgres", "generate-database-credential", ep, "-o", "json"))["token"]
user = json.loads(db("current-user", "me", "-o", "json"))["userName"]
env = {**os.environ, "PGPASSWORD": token}


def psql(sql, data=None):
    r = subprocess.run(["psql", f"host={host} user={user} dbname={args.database} sslmode=require",
                        "-v", "ON_ERROR_STOP=1", "-c", sql], capture_output=True, text=True, env=env, input=data)
    if r.returncode:
        raise SystemExit(r.stderr[-800:])
    return r.stdout


def fetch_csv(statement):
    body = {"warehouse_id": args.warehouse, "statement": statement, "wait_timeout": "50s",
            "on_wait_timeout": "CONTINUE", "disposition": "EXTERNAL_LINKS", "format": "CSV"}
    res = json.loads(db("api", "post", "/api/2.0/sql/statements", "--json", json.dumps(body)))
    sid = res["statement_id"]
    while res["status"]["state"] in ("PENDING", "RUNNING"):
        res = json.loads(db("api", "get", f"/api/2.0/sql/statements/{sid}"))
    if res["status"]["state"] != "SUCCEEDED":
        raise SystemExit(str(res["status"]))
    chunks = res["manifest"].get("total_chunk_count", 1)
    for i in range(chunks):
        info = res if i == 0 else json.loads(db("api", "get", f"/api/2.0/sql/statements/{sid}/result/chunks/{i}"))
        for link in info["result"]["external_links"]:
            with urllib.request.urlopen(link["external_link"]) as f:  # presigned URL, no auth header
                yield f.read().decode()


for tbl, pk in TABLES.items():
    full = f"{args.catalog}.{args.schema}.{tbl}"
    cols = json.loads(db("tables", "get", full, "-o", "json"))["columns"]
    ddl_cols = ", ".join(f'"{c["name"]}" {PG_TYPES.get(c["type_name"], "text")}' for c in cols)
    pkc = ", ".join(f'"{c}"' for c in pk)
    psql(f'DROP TABLE IF EXISTS public."{tbl}"; CREATE TABLE public."{tbl}" ({ddl_cols}, PRIMARY KEY ({pkc}));')
    names = ", ".join(f'"{c["name"]}"' for c in cols)
    n = 0
    for chunk in fetch_csv(f"SELECT * FROM {full}"):
        if chunk.startswith(cols[0]["name"] + ","):  # the CSV export repeats the header per statement
            chunk = chunk.split("\n", 1)[1]
        n += sum(1 for _ in csv.reader(io.StringIO(chunk)))
        r = subprocess.run(
            ["psql", f"host={host} user={user} dbname={args.database} sslmode=require", "-v", "ON_ERROR_STOP=1",
             "-c", f'COPY public."{tbl}" ({names}) FROM STDIN WITH (FORMAT csv, NULL \'null\')'],
            capture_output=True, text=True, env=env, input=chunk)
        if r.returncode:
            raise SystemExit(r.stderr[-600:] + chunk[:300])
    print(f"{tbl}: {n} rows loaded")
print("done")
