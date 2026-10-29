# Apex Mobility: One Governed Platform for Live Mobility Operations

## 1. The problem
Evening peak: ~1 in 4 requests find no driver, surge 2.15x. Premium fleet breaks down with no warning (avg risk 0.77). ~8.3% of telemetry is dirty. Stack is siloed (warehouse + BI + OSS ML + governance).

## 2. Solution at a glance
Lakeflow (ingest + DQ) -> Unity Catalog (PII, masks, ABAC) -> ML + Model Serving -> Genie (EN/Bahasa) -> Lakebase synced tables -> Databricks App with write-back. One DAB reproduces it.

## 3. Architecture
Raw telemetry -> bronze -> DQ pipeline (6 expectations, quarantine) -> curated gold -> {risk model, demand forecast} -> gold predictions -> Lakebase (OLTP serving + write-back) -> AppKit app. Genie and the AI/BI dashboard read the governed tables.

## 4. Demo flow
Command Center (live) -> Fleet and Forecast (what-if, approve service, write-back reflected on next read) -> Ask (Genie) -> Data Access (persona masking) -> Dashboard.

## 5. Decisions and trade-offs
Lakebase for sub-second reads; governance page on the warehouse so UC masks apply; serverless; Genie as a bundle resource; micro-batch not streaming.

## 6. How it was built with AI
Layer-by-layer with an AI assistant, each stage verified live with captured evidence. Bugs found and fixed (interval-units bug, serverless .cache()).

## 7. Outcomes
No-driver 24% -> ~15%; surge 2.15x -> ~1.6x; ~95 at-risk vehicles serviced proactively; platform consolidation. All data is synthetic.
