import psycopg2

conn = psycopg2.connect(host="localhost", port=5432, user="postgres", password="password", dbname="penlok_cloud")
cur = conn.cursor()

cur.execute("""
    SELECT 
        COUNT(*) as total,
        COUNT(*) FILTER (WHERE decision = 0) as edge_count,
        COUNT(*) FILTER (WHERE decision = 1) as cloud_count,
        ROUND(AVG(execution_time_ms) FILTER (WHERE decision = 0), 1) as avg_edge_time,
        ROUND(AVG(execution_time_ms) FILTER (WHERE decision = 1), 1) as avg_cloud_time,
        ROUND(AVG(cpu_pct) FILTER (WHERE decision = 0), 1) as avg_edge_cpu,
        ROUND(AVG(cpu_pct) FILTER (WHERE decision = 1), 1) as avg_cloud_cpu
    FROM mas_decision_history;
""")
summary = cur.fetchone()
print("Summary stats:", summary)

cur.execute("""
    SELECT id, task_id, timestamp, decision, decision_label, execution_node, model_used, cpu_pct, ram_pct, latency_ms, priority, queue_len, execution_time_ms, user_id, confidence, status, notes
    FROM mas_decision_history
    ORDER BY timestamp DESC, id DESC
    LIMIT 5;
""")
logs = cur.fetchall()
print("Top 5 recent logs:")
for l in logs:
    print(l)

conn.close()
