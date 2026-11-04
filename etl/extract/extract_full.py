
"""从 Source 层分批抽取交易数据。"""

# 每批查询的数据量
DEFAULT_BATCH_SIZE = 1000


def extract_transactions(conn, batch_size=DEFAULT_BATCH_SIZE):
    """
    全量抽取 source.transactions。

    参数：
        conn: PostgreSQL 数据库连接
        batch_size: 每批读取的记录数

    返回：
        使用 yield 逐批产生数据
    """

    if batch_size <= 0:
        raise ValueError("batch_size 必须大于 0")

    sql = """
        SELECT
            transaction_id,
            account_id,
            transaction_type,
            amount,
            transaction_status,
            transaction_time,
            created_at
        FROM source.transactions
        ORDER BY transaction_id
    """

    # 使用服务端游标，适合分批读取大表
    with conn.cursor(name="extract_transaction_cursor") as cur:

        cur.execute(sql)

        while True:

            # 每次读取最多 batch_size 条
            rows = cur.fetchmany(batch_size)

            # 没有剩余数据时结束
            if not rows:
                break

            # 返回当前批次给调用方
            yield rows
