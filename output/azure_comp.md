# PostgreSQL Comparative Diagnostic Report

**Generated:** 2025-10-17 22:10:11

## 📊 Server Information

- **Server 1 (Fast):** enatabread.postgres.database.azure.com:5432/postgres
- **Server 2 (Slow):** enatabreadprod.postgres.database.azure.com:5432/postgres

## 🔧 PostgreSQL Version & Configuration

Parameter                 Server 1    Server 2
------------------------  ----------  ----------
PostgreSQL Version        15.13       15.13
Max Connections           50          429
Shared Buffers            1GB         1GB
Effective Cache Size      3GB         3GB
Work Memory               4MB         4MB
Random Page Cost          2.0         2.0
Effective IO Concurrency  1           1
Synchronous Commit        on          on


## 🔌 Connection Statistics

Metric               Server 1    Server 2
-------------------  ----------  ----------
Current Connections  16          18
Max Connections      50          429
Active Connections   1           1
Idle Connections     7           9
Connection Usage %   32%         4%


## 💾 Cache Hit Ratio (CRITICAL)

Metric             Server 1    Server 2
-----------------  ----------  ----------
Heap Cache Hit %   56.37%      51.78%
Index Cache Hit %  98.52%      98.86%
Heap Blocks Read   3275400696  4393829567
Heap Blocks Hit    4232559851  4718159999

> ⚠️ **Cache hit ratio should be >95%**. Lower values indicate missing indexes or insufficient memory.

## 📦 Database Size

Metric         Server 1    Server 2
-------------  ----------  ----------
Database Size  101 GB      171 GB


## 📋 Table Statistics

Metric                   Server 1       Server 2
------------------  -------------  -------------
Total Tables        214            166
Avg Rows per Table    1.41658e+06    3.9845e+06
Max Rows in Table     4.6926e+07     3.52059e+08
Total Dead Rows       1.44208e+06    1.31398e+06


## 📑 Index Statistics

Metric            Server 1    Server 2
----------------  ----------  ----------
Total Indexes     130         133
Unused Indexes    58          62
Unused Indexes %  44.62%      46.62%
Avg Index Scans   3325936.58  4566252.35


## 🔒 Lock Statistics

Metric             Server 1    Server 2
---------------  ----------  ----------
Blocked Locks             0           0
Active Locks             26          26
Waiting Queries          15          16


## ⚡ Active Queries Now


### Server 1: No active queries


### Server 2: No active queries



## ⏱️ Long Running Queries


### Server 1 (7 queries)

  pid  usename      duration_hours  query_snippet
-----  ---------  ----------------  ------------------------------------------------------------------------------------------------------------------------------------------------------
  987  azuresu                0.41  SELECT query_stats.pgms_stats_insert_data(2862, '60
minutes')
  988  azuresu                0.05  SELECT query_store.staging_ws_data_reset()
25749  azuresu                0     commit
25763  azuresu                0     SELECT 1
25745  azuresu                0     SELECT slot.slot_name AS slot_name, slot.active AS active,
slot.slot_type AS slot_type,
pg_catalog.pg_current_wal_lsn()::TEXT AS current_wal_lsn,
pg_c
25750  azuresu                0     select (select case when pg_catalog.pg_is_in_recovery() then
(select lsn from public.pg_last_wal_replay_tli_lsn()) else
(pg_catalog.pg_current_wal_flu
25751  azuresu                0     select pg_catalog.now() at time zone 'utc' as info_ts_utc,
pg_catalog.pg_is_in_recovery() as pg_is_in_recovery, (select
count(*) from pg_catalog.pg_st

### Server 2 (9 queries)

   pid  usename           duration_hours  query_snippet
------  --------------  ----------------  ------------------------------------------------------------------------------------------------------------------------------------------------------
156226  enata_az_admin              1.29  SHOW search_path
156227  enata_az_admin              0.97  SELECT p.oid as
poid,p.*,pg_catalog.pg_get_expr(p.proargdefaults, 0) as
arg_defaults,d.description FROM pg_catalog.pg_proc p LEFT
OUTER JOIN pg_catalo
157331  enata_az_admin              0.91  SELECT c.oid, a.attnum, a.attname, c.relname, n.nspname,
a.attnotnull OR (t.typtype = 'd' AND t.typnotnull),
a.attidentity != '' OR pg_catalog.pg_get_
   985  azuresu                     0.65  SELECT query_stats.pgms_stats_insert_data(175, '60 minutes')
   986  azuresu                     0.15  SELECT query_store.staging_ws_data_reset()
165162  azuresu                     0     select (select case when pg_catalog.pg_is_in_recovery() then
(select lsn from public.pg_last_wal_replay_tli_lsn()) else
(pg_catalog.pg_current_wal_flu
165163  azuresu                     0     select pg_catalog.now() at time zone 'utc' as info_ts_utc,
pg_catalog.pg_is_in_recovery() as pg_is_in_recovery, (select
count(*) from pg_catalog.pg_st
165160  azuresu                     0     commit
165158  azuresu                     0     SELECT 1


## 🗑️ Table Bloat (Dead Rows)


### Server 1 (Tables with >1000 dead rows: 10)

schemaname               table_name                        live_rows    dead_rows    dead_rows_percent  table_size
-----------------------  ------------------------------  -----------  -----------  -------------------  ------------
enata_transformation     transformation_product_fact        41786491       594206                 1.4   14 GB
enata_posdata            order_items                        46926026       452328                 0.95  13 GB
enata_gostock_ingestion  havi_purchase_order_report_bck      1155034        70508                 5.75  242 MB
enata_gostock_data       products                             256114        45666                15.13  158 MB
enata_reports            pos_reports_end_amounts              278255        41612                13.01  46 MB
enata_posdata            orders                             25861800        40980                 0.16  10172 MB
enata_posdata            order_items_sub_items               6846013        38613                 0.56  1659 MB
enata_xreportingmart     xdailyreport_sales_channel         13211089        33164                 0.25  1809 MB
enata_posdata            removed_order_items                 2234048        31410                 1.39  774 MB
enata_reports            pos_reports_paids                     88651        13998                13.64  21 MB

### Server 2 (Tables with >1000 dead rows: 10)

schemaname            table_name                     live_rows    dead_rows    dead_rows_percent  table_size
--------------------  ---------------------------  -----------  -----------  -------------------  ------------
enata_posdata         order_items                     44542252       419729                 0.93  12 GB
enata_posdata         orders                          25031003       264245                 1.04  10047 MB
enata_transformation  transformation_product_fact     39263972       190855                 0.48  13 GB
enata_gostock_data    sales_order_items               23456616       118886                 0.5   6289 MB
enata_gostock_data    sales_orders                    11606555        68005                 0.58  3454 MB
enata_posdata         order_transactions              24405716        54945                 0.22  5967 MB
enata_reports         pos_reports_end_amounts           276897        46279                14.32  44 MB
enata_gostock_data    product_components                267836        34713                11.47  58 MB
enata_gostock_data    products                          255018        26286                 9.34  98 MB
enata_posdata         order_items_sub_items            6389612        25708                 0.4   1550 MB


## ⚠️ Query Performance Issues


### Server 1 (Issues found: 15)

schemaname               table_name                          seq_vs_idx_diff    seq_scan    idx_scan  issue_type        table_size
-----------------------  --------------------------------  -----------------  ----------  ----------  ----------------  ------------
enata_xjush              dim_jush_dark_store                           29583       29643          60  FULL_TABLE_SCANS  72 kB
enata_xreportingmart     xdailyreport_product_matrix                    1451        1451           0  MISSING_INDEX     6869 MB
enata_xreportingmart     xdailyreport_kiosk                              615         672          57  FULL_TABLE_SCANS  11 MB
enata_transformation     transformation_invoices_fact                    437         437           0  MISSING_INDEX     5704 kB
cron                     job                                             181         190           9  FULL_TABLE_SCANS  48 kB
enata_transformation     order_transactions_wd                           184         184           0  MISSING_INDEX     658 MB
enata_transformation     transformation_product_jush                      58          61           3  FULL_TABLE_SCANS  424 kB
enata_transformation     product_fact_discrepancies                       54          54           0  FULL_TABLE_SCANS  5560 kB
enata_xreportingmart     xplanning_data                                   21          21           0  FULL_TABLE_SCANS  278 MB
enata_gostock_ingestion  havi_purchase_order_report                       17          17           0  FULL_TABLE_SCANS  144 MB
enata_xjush              zamowienia_batch_log                             11          11           0  FULL_TABLE_SCANS  32 kB
enata_margin_calc        havi_delivery_costs                               9           9           0  FULL_TABLE_SCANS  864 kB
python_exp               py_margin_sales_report                            6           6           0  FULL_TABLE_SCANS  28 MB
enata_posdata            order_tax_items                                   4           4           0  FULL_TABLE_SCANS  5510 MB
enata_xjush              dm_jush_output_adj_conflict_lo
g                  4           4           0  FULL_TABLE_SCANS  48 kB

### Server 2 (Issues found: 15)

schemaname               table_name                        seq_vs_idx_diff    seq_scan    idx_scan  issue_type        table_size
-----------------------  ------------------------------  -----------------  ----------  ----------  ----------------  ------------
enata_posdata            sync_tracking                                 737         750          13  FULL_TABLE_SCANS  72 kB
enata_gostock_config     column_mappings                               711         711           0  MISSING_INDEX     32 kB
enata_transformation     transformation_invoices_fact                  673         673           0  MISSING_INDEX     3696 kB
enata_gostock_ingestion  havi_purchase_order_report                    424         431           7  FULL_TABLE_SCANS  282 MB
enata_xreportingmart     xdailyreport_product_matrix                   296         320          24  FULL_TABLE_SCANS  2221 MB
enata_card_transaction   pekao_daily_transaction                       306         308           2  FULL_TABLE_SCANS  4792 MB
enata_xreportingmart     konkurs_kawa_agregat                           82          87           5  FULL_TABLE_SCANS  399 MB
enata_gostock_ingestion  havi_purchase_order_report_bck                 35          35           0  FULL_TABLE_SCANS  66 MB
enata_analysis           konkurs_product_matrix                         33          33           0  FULL_TABLE_SCANS  764 MB
enata_dotykacka          clouds                                         14          14           0  FULL_TABLE_SCANS  40 kB
enata_dotykacka          branches                                        9           9           0  FULL_TABLE_SCANS  40 kB
enata_dotykacka          products                                        7           7           0  FULL_TABLE_SCANS  21 MB
enata_dotykacka          orders                                          7           7           0  FULL_TABLE_SCANS  56 MB
enata_gostock_data       purchase_order_items                            6           6           0  FULL_TABLE_SCANS  28 MB
enata_dotykacka          order_items                                     6           6           0  FULL_TABLE_SCANS  108 MB


## 🧹 Autovacuum Statistics


### Server 1

schemaname     table_name              last_vacuum    last_autovacuum                   last_analyze    last_autoanalyze                    vacuum_count    autovacuum_count    analyze_count    autoanalyze_count
-------------  ----------------------  -------------  --------------------------------  --------------  --------------------------------  --------------  ------------------  ---------------  -------------------
enata_posdata  modifier_group_options                 2025-10-17 20:07:42.540394+00:00                  2025-10-17 20:06:52.258276+00:00               0                9962                0                13190
enata_posdata  modifier_groups                        2025-10-17 20:07:42.497324+00:00                  2025-10-17 20:06:49.572503+00:00               0               12110                0                14817
enata_posdata  items                                  2025-10-17 20:07:42.492592+00:00                  2025-10-17 20:06:48.891566+00:00               0                8103                0                15151
enata_posdata  categories                             2025-10-17 20:07:42.358342+00:00                  2025-10-17 20:06:42.746629+00:00               0               12213                0                14793
enata_posdata  payment_methods                        2025-10-17 20:05:42.752433+00:00                  2025-10-17 20:06:42.875302+00:00               0               11457                0                11739

### Server 2

schemaname            table_name                    last_vacuum    last_autovacuum                   last_analyze    last_autoanalyze                    vacuum_count    autovacuum_count    analyze_count    autoanalyze_count
--------------------  ----------------------------  -------------  --------------------------------  --------------  --------------------------------  --------------  ------------------  ---------------  -------------------
enata_posdata         organization                                 2025-10-17 20:00:59.548624+00:00                  2025-10-17 20:00:59.555394+00:00               0               23223                0                 6475
enata_posdata         items                                        2025-10-17 14:01:17.180335+00:00                  2025-10-17 17:01:01.451011+00:00               0               34668                0                24759
enata_posdata         categories                                   2025-10-17 09:06:59.136463+00:00                  2025-10-17 18:01:06.118904+00:00               0               34156                0                22740
enata_transformation  transformation_invoices_fact                 2025-10-17 04:31:43.335853+00:00                  2025-10-17 02:58:46.672986+00:00               0               31723                0                  225
enata_gostock_data    stocks                                       2025-10-17 00:15:41.119415+00:00                  2025-10-17 00:13:44.996155+00:00               0                2635                0                  247


## 💾 Memory Configuration

Parameter                Server 1    Server 2
-----------------------  ----------  ----------
Shared Buffers           1GB         1GB
Effective Cache Size     3GB         3GB
Work Memory              4MB         4MB
Maintenance Work Memory  154MB       154MB


## 🎯 Analysis & Recommendations


✅ **Cache Hit Ratio**: Similar between servers

