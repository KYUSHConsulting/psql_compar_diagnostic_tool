#!/usr/bin/env python3
"""
PostgreSQL Comparative Diagnostic Tool
Compare two servers to identify performance issues
Generates detailed markdown report for analysis
"""

import os
import sys
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, asdict
import argparse
from tabulate import tabulate
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class ServerConfig:
    """Server configuration"""
    name: str
    host: str
    database: str
    user: str
    password: str
    port: int = 5432


@dataclass
class MetricComparison:
    """Metric comparison result"""
    metric_name: str
    server1_value: str
    server2_value: str
    unit: str
    difference: str
    status: str  # 'GOOD', 'WARNING', 'CRITICAL'


class PostgreSQLComparativeDiagnostic:
    """Comparative diagnostic tool for two PostgreSQL servers"""

    def __init__(self, server1: ServerConfig, server2: ServerConfig):
        """Initialize with two servers"""
        self.server1 = server1
        self.server2 = server2
        self.conn1 = None
        self.conn2 = None
        self.connect()

    def connect(self):
        """Connect to both servers"""
        try:
            self.conn1 = psycopg2.connect(
                host=self.server1.host,
                database=self.server1.database,
                user=self.server1.user,
                password=self.server1.password,
                port=self.server1.port
            )
            logger.info(f"✅ Connected to {self.server1.name}")
        except Exception as e:
            logger.error(f"❌ Failed to connect to {self.server1.name}: {e}")
            sys.exit(1)

        try:
            self.conn2 = psycopg2.connect(
                host=self.server2.host,
                database=self.server2.database,
                user=self.server2.user,
                password=self.server2.password,
                port=self.server2.port
            )
            logger.info(f"✅ Connected to {self.server2.name}")
        except Exception as e:
            logger.error(f"❌ Failed to connect to {self.server2.name}: {e}")
            sys.exit(1)

    def execute_query(self, conn: psycopg2.extensions.connection, query: str) -> List[Dict]:
        """Execute query on given connection"""
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query)
                return cur.fetchall()
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            return []

    # ========== DIAGNOSTIC QUERIES ==========

    def get_version_info(self, conn: psycopg2.extensions.connection) -> Dict:
        """Get PostgreSQL version and settings"""
        query = """
        SELECT 
            version() as version,
            current_setting('server_version') as pg_version,
            current_setting('max_connections')::int as max_connections,
            current_setting('shared_buffers') as shared_buffers,
            current_setting('effective_cache_size') as effective_cache_size,
            current_setting('work_mem') as work_mem,
            current_setting('maintenance_work_mem') as maintenance_work_mem,
            current_setting('random_page_cost')::float as random_page_cost,
            current_setting('effective_io_concurrency')::int as effective_io_concurrency,
            current_setting('synchronous_commit') as synchronous_commit,
            current_setting('wal_level') as wal_level
        """
        result = self.execute_query(conn, query)
        return result[0] if result else {}

    def get_connection_stats(self, conn: psycopg2.extensions.connection) -> Dict:
        """Get connection statistics"""
        query = """
        SELECT 
            (SELECT count(*) FROM pg_stat_activity) as current_connections,
            (SELECT setting::int FROM pg_settings WHERE name = 'max_connections') as max_connections,
            (SELECT count(*) FROM pg_stat_activity WHERE state = 'active') as active_connections,
            (SELECT count(*) FROM pg_stat_activity WHERE state = 'idle') as idle_connections,
            (SELECT ROUND(100.0 * count(*) / (SELECT setting::int FROM pg_settings WHERE name = 'max_connections')) 
             FROM pg_stat_activity) as connection_usage_percent
        """
        result = self.execute_query(conn, query)
        return result[0] if result else {}

    def get_cache_hit_ratio(self, conn: psycopg2.extensions.connection) -> Dict:
        """Get cache hit ratio"""
        query = """
        SELECT 
            sum(heap_blks_read) as heap_read,
            sum(heap_blks_hit) as heap_hit,
            ROUND(100.0 * sum(heap_blks_hit) / NULLIF(sum(heap_blks_hit) + sum(heap_blks_read), 0), 2) as cache_hit_percent,
            sum(idx_blks_read) as idx_read,
            sum(idx_blks_hit) as idx_hit,
            ROUND(100.0 * sum(idx_blks_hit) / NULLIF(sum(idx_blks_hit) + sum(idx_blks_read), 0), 2) as idx_cache_hit_percent
        FROM pg_statio_user_tables
        """
        result = self.execute_query(conn, query)
        return result[0] if result else {}

    def get_database_size(self, conn: psycopg2.extensions.connection) -> Dict:
        """Get database size"""
        query = """
        SELECT 
            pg_size_pretty(pg_database_size(current_database())) as database_size,
            pg_database_size(current_database()) as database_size_bytes
        """
        result = self.execute_query(conn, query)
        return result[0] if result else {}

    def get_table_count_and_stats(self, conn: psycopg2.extensions.connection) -> Dict:
        """Get table statistics"""
        query = """
        SELECT 
            count(*) as total_tables,
            ROUND(AVG(n_live_tup)::numeric, 0) as avg_rows_per_table,
            MAX(n_live_tup) as max_rows_in_table,
            ROUND(AVG(n_dead_tup)::numeric, 0) as avg_dead_rows,
            SUM(n_dead_tup) as total_dead_rows
        FROM pg_stat_user_tables
        """
        result = self.execute_query(conn, query)
        return result[0] if result else {}

    def get_index_stats(self, conn: psycopg2.extensions.connection) -> Dict:
        """Get index statistics"""
        query = """
        SELECT 
            count(*) as total_indexes,
            sum(CASE WHEN idx_scan = 0 THEN 1 ELSE 0 END) as unused_indexes,
            ROUND(100.0 * sum(CASE WHEN idx_scan = 0 THEN 1 ELSE 0 END) / count(*), 2) as unused_indexes_percent,
            ROUND(AVG(idx_scan)::numeric, 2) as avg_index_scans
        FROM pg_stat_user_indexes
        """
        result = self.execute_query(conn, query)
        return result[0] if result else {}

    def get_active_queries(self, conn: psycopg2.extensions.connection) -> List[Dict]:
        """Get active queries"""
        query = """
        SELECT 
            pid,
            usename,
            state,
            ROUND(EXTRACT(EPOCH FROM (NOW() - query_start))::numeric, 2) as duration_sec,
            LEFT(query, 150) as query_snippet
        FROM pg_stat_activity
        WHERE state = 'active' AND pid <> pg_backend_pid()
        ORDER BY query_start ASC
        LIMIT 20
        """
        return self.execute_query(conn, query)

    def get_longest_queries(self, conn: psycopg2.extensions.connection) -> List[Dict]:
        """Get longest running queries"""
        query = """
        SELECT 
            pid,
            usename,
            ROUND(EXTRACT(EPOCH FROM (NOW() - query_start))::numeric / 3600, 2) as duration_hours,
            LEFT(query, 150) as query_snippet
        FROM pg_stat_activity
        WHERE pid <> pg_backend_pid() AND query_start IS NOT NULL
        ORDER BY query_start ASC
        LIMIT 10
        """
        return self.execute_query(conn, query)

    def get_table_bloat(self, conn: psycopg2.extensions.connection) -> List[Dict]:
        """Get table bloat info"""
        query = """
        SELECT 
            schemaname,
            relname as table_name,
            n_live_tup as live_rows,
            n_dead_tup as dead_rows,
            ROUND(100.0 * n_dead_tup / NULLIF(n_live_tup + n_dead_tup, 0), 2) as dead_rows_percent,
            pg_size_pretty(pg_total_relation_size(schemaname||'.'||relname)) as table_size
        FROM pg_stat_user_tables
        WHERE n_dead_tup > 1000
        ORDER BY n_dead_tup DESC
        LIMIT 10
        """
        return self.execute_query(conn, query)

    def get_autovacuum_stats(self, conn: psycopg2.extensions.connection) -> List[Dict]:
        """Get autovacuum statistics"""
        query = """
        SELECT 
            schemaname,
            relname as table_name,
            last_vacuum,
            last_autovacuum,
            last_analyze,
            last_autoanalyze,
            vacuum_count,
            autovacuum_count,
            analyze_count,
            autoanalyze_count
        FROM pg_stat_user_tables
        ORDER BY last_autovacuum DESC NULLS LAST
        LIMIT 10
        """
        return self.execute_query(conn, query)

    def get_query_performance_issues(self, conn: psycopg2.extensions.connection) -> List[Dict]:
        """Get potential query performance issues"""
        query = """
        SELECT 
            schemaname,
            relname as table_name,
            ROUND(seq_scan - idx_scan::numeric, 0) as seq_vs_idx_diff,
            seq_scan,
            idx_scan,
            CASE 
                WHEN idx_scan = 0 AND seq_scan > 100 THEN 'MISSING_INDEX'
                WHEN seq_scan > idx_scan * 10 THEN 'FULL_TABLE_SCANS'
                ELSE 'OK'
            END as issue_type,
            pg_size_pretty(pg_total_relation_size(schemaname||'.'||relname)) as table_size
        FROM pg_stat_user_tables
        WHERE (idx_scan = 0 AND seq_scan > 100) OR (seq_scan > idx_scan * 10)
        ORDER BY seq_scan DESC
        LIMIT 15
        """
        return self.execute_query(conn, query)

    def get_lock_stats(self, conn: psycopg2.extensions.connection) -> Dict:
        """Get lock statistics"""
        query = """
        SELECT 
            (SELECT count(*) FROM pg_locks WHERE NOT granted) as blocked_locks,
            (SELECT count(*) FROM pg_locks WHERE granted) as active_locks,
            (SELECT count(*) FROM pg_stat_activity WHERE wait_event_type IS NOT NULL) as waiting_queries
        """
        result = self.execute_query(conn, query)
        return result[0] if result else {}

    def get_memory_stats(self, conn: psycopg2.extensions.connection) -> Dict:
        """Get memory configuration"""
        query = """
        SELECT 
            current_setting('shared_buffers') as shared_buffers,
            current_setting('effective_cache_size') as effective_cache_size,
            current_setting('work_mem') as work_mem,
            current_setting('maintenance_work_mem') as maintenance_work_mem,
            CASE 
                WHEN (SELECT setting::bigint FROM pg_settings WHERE name = 'shared_buffers') < 1000000 THEN 'LOW'
                WHEN (SELECT setting::bigint FROM pg_settings WHERE name = 'shared_buffers') < 4000000 THEN 'MEDIUM'
                ELSE 'HIGH'
            END as shared_buffers_level
        """
        result = self.execute_query(conn, query)
        return result[0] if result else {}

    # ========== REPORTING ==========

    def generate_markdown_report(self) -> str:
        """Generate comprehensive markdown comparison report"""
        
        report = []
        report.append("# PostgreSQL Comparative Diagnostic Report")
        report.append(f"\n**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

        # Server info
        report.append("## 📊 Server Information\n")
        report.append(f"- **Server 1 (Fast):** {self.server1.host}:{self.server1.port}/{self.server1.database}")
        report.append(f"- **Server 2 (Slow):** {self.server2.host}:{self.server2.port}/{self.server2.database}\n")

        # Version comparison
        report.append("## 🔧 PostgreSQL Version & Configuration\n")
        v1 = self.get_version_info(self.conn1)
        v2 = self.get_version_info(self.conn2)
        
        version_table = [
            ["PostgreSQL Version", v1.get('pg_version', 'N/A'), v2.get('pg_version', 'N/A')],
            ["Max Connections", v1.get('max_connections', 'N/A'), v2.get('max_connections', 'N/A')],
            ["Shared Buffers", v1.get('shared_buffers', 'N/A'), v2.get('shared_buffers', 'N/A')],
            ["Effective Cache Size", v1.get('effective_cache_size', 'N/A'), v2.get('effective_cache_size', 'N/A')],
            ["Work Memory", v1.get('work_mem', 'N/A'), v2.get('work_mem', 'N/A')],
            ["Random Page Cost", v1.get('random_page_cost', 'N/A'), v2.get('random_page_cost', 'N/A')],
            ["Effective IO Concurrency", v1.get('effective_io_concurrency', 'N/A'), v2.get('effective_io_concurrency', 'N/A')],
            ["Synchronous Commit", v1.get('synchronous_commit', 'N/A'), v2.get('synchronous_commit', 'N/A')],
        ]
        report.append(tabulate(version_table, headers=["Parameter", "Server 1", "Server 2"], tablefmt="markdown"))
        report.append("\n")

        # Connection stats
        report.append("## 🔌 Connection Statistics\n")
        c1 = self.get_connection_stats(self.conn1)
        c2 = self.get_connection_stats(self.conn2)
        
        conn_table = [
            ["Current Connections", c1.get('current_connections', 'N/A'), c2.get('current_connections', 'N/A')],
            ["Max Connections", c1.get('max_connections', 'N/A'), c2.get('max_connections', 'N/A')],
            ["Active Connections", c1.get('active_connections', 'N/A'), c2.get('active_connections', 'N/A')],
            ["Idle Connections", c1.get('idle_connections', 'N/A'), c2.get('idle_connections', 'N/A')],
            ["Connection Usage %", f"{c1.get('connection_usage_percent', 'N/A')}%", f"{c2.get('connection_usage_percent', 'N/A')}%"],
        ]
        report.append(tabulate(conn_table, headers=["Metric", "Server 1", "Server 2"], tablefmt="markdown"))
        report.append("\n")

        # Cache hit ratio (CRITICAL!)
        report.append("## 💾 Cache Hit Ratio (CRITICAL)\n")
        cache1 = self.get_cache_hit_ratio(self.conn1)
        cache2 = self.get_cache_hit_ratio(self.conn2)
        
        cache_table = [
            ["Heap Cache Hit %", f"{cache1.get('cache_hit_percent', 'N/A')}%", f"{cache2.get('cache_hit_percent', 'N/A')}%"],
            ["Index Cache Hit %", f"{cache1.get('idx_cache_hit_percent', 'N/A')}%", f"{cache2.get('idx_cache_hit_percent', 'N/A')}%"],
            ["Heap Blocks Read", cache1.get('heap_read', 'N/A'), cache2.get('heap_read', 'N/A')],
            ["Heap Blocks Hit", cache1.get('heap_hit', 'N/A'), cache2.get('heap_hit', 'N/A')],
        ]
        report.append(tabulate(cache_table, headers=["Metric", "Server 1", "Server 2"], tablefmt="markdown"))
        report.append("\n> ⚠️ **Cache hit ratio should be >95%**. Lower values indicate missing indexes or insufficient memory.\n")

        # Database size
        report.append("## 📦 Database Size\n")
        db1 = self.get_database_size(self.conn1)
        db2 = self.get_database_size(self.conn2)
        
        size_table = [
            ["Database Size", db1.get('database_size', 'N/A'), db2.get('database_size', 'N/A')],
        ]
        report.append(tabulate(size_table, headers=["Metric", "Server 1", "Server 2"], tablefmt="markdown"))
        report.append("\n")

        # Table statistics
        report.append("## 📋 Table Statistics\n")
        tbl1 = self.get_table_count_and_stats(self.conn1)
        tbl2 = self.get_table_count_and_stats(self.conn2)
        
        table_stats = [
            ["Total Tables", tbl1.get('total_tables', 'N/A'), tbl2.get('total_tables', 'N/A')],
            ["Avg Rows per Table", tbl1.get('avg_rows_per_table', 'N/A'), tbl2.get('avg_rows_per_table', 'N/A')],
            ["Max Rows in Table", tbl1.get('max_rows_in_table', 'N/A'), tbl2.get('max_rows_in_table', 'N/A')],
            ["Total Dead Rows", tbl1.get('total_dead_rows', 'N/A'), tbl2.get('total_dead_rows', 'N/A')],
        ]
        report.append(tabulate(table_stats, headers=["Metric", "Server 1", "Server 2"], tablefmt="markdown"))
        report.append("\n")

        # Index statistics
        report.append("## 📑 Index Statistics\n")
        idx1 = self.get_index_stats(self.conn1)
        idx2 = self.get_index_stats(self.conn2)
        
        index_stats = [
            ["Total Indexes", idx1.get('total_indexes', 'N/A'), idx2.get('total_indexes', 'N/A')],
            ["Unused Indexes", idx1.get('unused_indexes', 'N/A'), idx2.get('unused_indexes', 'N/A')],
            ["Unused Indexes %", f"{idx1.get('unused_indexes_percent', 'N/A')}%", f"{idx2.get('unused_indexes_percent', 'N/A')}%"],
            ["Avg Index Scans", idx1.get('avg_index_scans', 'N/A'), idx2.get('avg_index_scans', 'N/A')],
        ]
        report.append(tabulate(index_stats, headers=["Metric", "Server 1", "Server 2"], tablefmt="markdown"))
        report.append("\n")

        # Lock statistics
        report.append("## 🔒 Lock Statistics\n")
        lock1 = self.get_lock_stats(self.conn1)
        lock2 = self.get_lock_stats(self.conn2)
        
        lock_stats = [
            ["Blocked Locks", lock1.get('blocked_locks', 'N/A'), lock2.get('blocked_locks', 'N/A')],
            ["Active Locks", lock1.get('active_locks', 'N/A'), lock2.get('active_locks', 'N/A')],
            ["Waiting Queries", lock1.get('waiting_queries', 'N/A'), lock2.get('waiting_queries', 'N/A')],
        ]
        report.append(tabulate(lock_stats, headers=["Metric", "Server 1", "Server 2"], tablefmt="markdown"))
        report.append("\n")

        # Active queries
        report.append("## ⚡ Active Queries Now\n")
        act1 = self.get_active_queries(self.conn1)
        act2 = self.get_active_queries(self.conn2)
        
        if act1:
            report.append(f"\n### Server 1 ({len(act1)} active)\n")
            report.append(tabulate(act1, headers="keys", tablefmt="markdown", maxcolwidths=[None, None, None, 10, 60]))
        else:
            report.append("\n### Server 1: No active queries\n")
        
        if act2:
            report.append(f"\n### Server 2 ({len(act2)} active)\n")
            report.append(tabulate(act2, headers="keys", tablefmt="markdown", maxcolwidths=[None, None, None, 10, 60]))
        else:
            report.append("\n### Server 2: No active queries\n")
        report.append("\n")

        # Long running queries
        report.append("## ⏱️ Long Running Queries\n")
        long1 = self.get_longest_queries(self.conn1)
        long2 = self.get_longest_queries(self.conn2)
        
        if long1:
            report.append(f"\n### Server 1 ({len(long1)} queries)\n")
            report.append(tabulate(long1, headers="keys", tablefmt="markdown", maxcolwidths=[None, None, 10, 60]))
        else:
            report.append("\n### Server 1: No long running queries\n")
        
        if long2:
            report.append(f"\n### Server 2 ({len(long2)} queries)\n")
            report.append(tabulate(long2, headers="keys", tablefmt="markdown", maxcolwidths=[None, None, 10, 60]))
        else:
            report.append("\n### Server 2: No long running queries\n")
        report.append("\n")

        # Table bloat
        report.append("## 🗑️ Table Bloat (Dead Rows)\n")
        bloat1 = self.get_table_bloat(self.conn1)
        bloat2 = self.get_table_bloat(self.conn2)
        
        if bloat1:
            report.append(f"\n### Server 1 (Tables with >1000 dead rows: {len(bloat1)})\n")
            report.append(tabulate(bloat1, headers="keys", tablefmt="markdown", maxcolwidths=[None, 30, None, None, None, None, None]))
        else:
            report.append("\n### Server 1: No significant table bloat\n")
        
        if bloat2:
            report.append(f"\n### Server 2 (Tables with >1000 dead rows: {len(bloat2)})\n")
            report.append(tabulate(bloat2, headers="keys", tablefmt="markdown", maxcolwidths=[None, 30, None, None, None, None, None]))
        else:
            report.append("\n### Server 2: No significant table bloat\n")
        report.append("\n")

        # Query performance issues
        report.append("## ⚠️ Query Performance Issues\n")
        perf1 = self.get_query_performance_issues(self.conn1)
        perf2 = self.get_query_performance_issues(self.conn2)
        
        if perf1:
            report.append(f"\n### Server 1 (Issues found: {len(perf1)})\n")
            report.append(tabulate(perf1, headers="keys", tablefmt="markdown", maxcolwidths=[None, 30, None, None, None, 20, None]))
        else:
            report.append("\n### Server 1: No query performance issues detected\n")
        
        if perf2:
            report.append(f"\n### Server 2 (Issues found: {len(perf2)})\n")
            report.append(tabulate(perf2, headers="keys", tablefmt="markdown", maxcolwidths=[None, 30, None, None, None, 20, None]))
        else:
            report.append("\n### Server 2: No query performance issues detected\n")
        report.append("\n")

        # Autovacuum stats
        report.append("## 🧹 Autovacuum Statistics\n")
        vac1 = self.get_autovacuum_stats(self.conn1)
        vac2 = self.get_autovacuum_stats(self.conn2)
        
        if vac1:
            report.append(f"\n### Server 1\n")
            report.append(tabulate(vac1[:5], headers="keys", tablefmt="markdown", maxcolwidths=[None, 30, None, None, None, None, None, None, None, None, None]))
        
        if vac2:
            report.append(f"\n### Server 2\n")
            report.append(tabulate(vac2[:5], headers="keys", tablefmt="markdown", maxcolwidths=[None, 30, None, None, None, None, None, None, None, None, None]))
        report.append("\n")

        # Memory configuration
        report.append("## 💾 Memory Configuration\n")
        mem1 = self.get_memory_stats(self.conn1)
        mem2 = self.get_memory_stats(self.conn2)
        
        mem_table = [
            ["Shared Buffers", mem1.get('shared_buffers', 'N/A'), mem2.get('shared_buffers', 'N/A')],
            ["Effective Cache Size", mem1.get('effective_cache_size', 'N/A'), mem2.get('effective_cache_size', 'N/A')],
            ["Work Memory", mem1.get('work_mem', 'N/A'), mem2.get('work_mem', 'N/A')],
            ["Maintenance Work Memory", mem1.get('maintenance_work_mem', 'N/A'), mem2.get('maintenance_work_mem', 'N/A')],
        ]
        report.append(tabulate(mem_table, headers=["Parameter", "Server 1", "Server 2"], tablefmt="markdown"))
        report.append("\n")

        # Analysis & recommendations
        report.append("## 🎯 Analysis & Recommendations\n\n")
        report.append(self.generate_recommendations(v1, v2, cache1, cache2, c1, c2, idx1, idx2))
        report.append("\n")

        return "\n".join(report)

    def generate_recommendations(self, v1, v2, cache1, cache2, c1, c2, idx1, idx2) -> str:
        """Generate recommendations based on comparison"""
        
        recommendations = []
        
        # Cache hit ratio analysis
        cache_diff = float(cache2.get('cache_hit_percent', 0) or 0) - float(cache1.get('cache_hit_percent', 0) or 0)
        if cache_diff < -10:
            recommendations.append(f"❌ **Cache Hit Ratio**: Server 2 has {abs(cache_diff):.1f}% lower cache hit ratio. This is likely the PRIMARY performance issue.")
            recommendations.append("   - **Fix**: Check for missing indexes on Server 2")
            recommendations.append("   - **Fix**: Increase `shared_buffers` and `effective_cache_size` on Server 2")
            recommendations.append("   - **Fix**: Analyze queries with high sequential scans vs index scans")
        else:
            recommendations.append(f"✅ **Cache Hit Ratio**: Similar between servers")

        # Connection usage
        conn_diff = int(c2.get('connection_usage_percent', 0) or 0) - int(c1.get('connection_usage_percent', 0) or 0)
        if conn_diff > 20:
            recommendations.append(f"\n❌ **Connection Pool**: Server 2 has {conn_diff}% higher connection usage")
            recommendations.append("   - **Fix**: Identify connection leaks in application")
            recommendations.append("   - **Fix**: Implement connection pooling (PgBouncer)")

        # Index issues
        unused_diff = float(idx2.get('unused_indexes_percent', 0) or 0) - float(idx1.get('unused_indexes_percent', 0) or 0)
        if unused_diff > 5:
            recommendations.append(f"\n❌ **Index Usage**: Server 2 has {unused_diff:.1f}% more unused indexes")
            recommendations.append("   - **Fix**: Drop unused indexes to free disk space and improve writes")

        # Memory configuration
        if v1.get('shared_buffers') != v2.get('shared_buffers'):
            recommendations.append(f"\n⚠️ **Memory Config**: Different `shared_buffers` settings")
            recommendations.append(f"   - Server 1: {v1.get('shared_buffers')}")
            recommendations.append(f"   - Server 2: {v2.get('shared_buffers')}")
            recommendations.append("   - **Fix**: Align settings or upgrade Server 2 configuration")

        if not recommendations:
            recommendations.append("✅ No major differences found. Issue may be application-level or related to data patterns.")

        return "\n".join(recommendations)

    def close(self):
        """Close connections"""
        if self.conn1:
            self.conn1.close()
        if self.conn2:
            self.conn2.close()


# ========== CLI ==========

def main():
    parser = argparse.ArgumentParser(
        description="PostgreSQL Comparative Diagnostic Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s \\
    --server1-host fast.postgres.database.azure.com \\
    --server1-db mydb --server1-user admin --server1-pass pass1 \\
    --server2-host slow.postgres.database.azure.com \\
    --server2-db mydb --server2-user admin --server2-pass pass2 \\
    --output azure_comp.md

  Or use environment variables:
    export PG1_HOST="fast.postgres.database.azure.com"
    export PG1_DB="mydb"
    export PG1_USER="admin"
    export PG1_PASS="password"
    export PG2_HOST="slow.postgres.database.azure.com"
    export PG2_DB="mydb"
    export PG2_USER="admin"
    export PG2_PASS="password"
    
    %(prog)s --output azure_comp.md
        """
    )

    # Server 1 (Fast)
    parser.add_argument("--server1-host", default=os.getenv("PG1_HOST"))
    parser.add_argument("--server1-db", default=os.getenv("PG1_DB"))
    parser.add_argument("--server1-user", default=os.getenv("PG1_USER"))
    parser.add_argument("--server1-pass", default=os.getenv("PG1_PASS"))
    parser.add_argument("--server1-port", type=int, default=int(os.getenv("PG1_PORT", "5432")))

    # Server 2 (Slow)
    parser.add_argument("--server2-host", default=os.getenv("PG2_HOST"))
    parser.add_argument("--server2-db", default=os.getenv("PG2_DB"))
    parser.add_argument("--server2-user", default=os.getenv("PG2_USER"))
    parser.add_argument("--server2-pass", default=os.getenv("PG2_PASS"))
    parser.add_argument("--server2-port", type=int, default=int(os.getenv("PG2_PORT", "5432")))

    # Output
    parser.add_argument("--output", default="azure_comparison.md", help="Output report file (markdown)")
    parser.add_argument("--format", choices=["markdown", "json"], default="markdown", help="Output format")

    args = parser.parse_args()

    # Validate inputs
    required_args = [
        args.server1_host, args.server1_db, args.server1_user, args.server1_pass,
        args.server2_host, args.server2_db, args.server2_user, args.server2_pass
    ]

    if not all(required_args):
        parser.print_help()
        logger.error("❌ Missing required arguments. Use environment variables or command-line args.")
        sys.exit(1)

    # Create server configs
    server1 = ServerConfig(
        name="Server1-Fast",
        host=args.server1_host,
        database=args.server1_db,
        user=args.server1_user,
        password=args.server1_pass,
        port=args.server1_port
    )

    server2 = ServerConfig(
        name="Server2-Slow",
        host=args.server2_host,
        database=args.server2_db,
        user=args.server2_user,
        password=args.server2_pass,
        port=args.server2_port
    )

    # Run diagnostic
    logger.info("🚀 Starting comparative diagnostic...")
    diag = PostgreSQLComparativeDiagnostic(server1, server2)

    try:
        if args.format == "markdown":
            report = diag.generate_markdown_report()
        else:
            report = json.dumps({
                "server1": server1.__dict__,
                "server2": server2.__dict__,
                "report": "JSON format not yet implemented"
            }, indent=2)

        # Write to file
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(report)

        logger.info(f"✅ Report saved to: {args.output}")
        print(f"\n📊 Report generated successfully!")
        print(f"📄 File: {args.output}")

    finally:
        diag.close()


if __name__ == "__main__":
    main()