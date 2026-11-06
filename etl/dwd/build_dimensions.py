
"""
D15 - 银行数据仓库维度装载

功能：
1. Source 客户地区 -> dim_region
2. Source 客户 -> dim_customer
3. 检查维度主键和数据完整性
4. 支持重复执行（UPSERT）

运行：
python etl/dwd/build_dimensions.py

依赖：
pip install psycopg[binary] python-dotenv
"""

import sys
import logging
from pathlib import Path

# 项目根目录：etl/dwd/build_dimensions.py -> etl/dwd -> etl -> 项目根
PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from etl.common.db import get_connection


# ============================================================
# 2. 日志
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

logger = logging.getLogger(__name__)


# ============================================================
# 3. 地区维度装载
# ============================================================

LOAD_REGION_SQL = """
INSERT INTO dwd.dim_region (
    region_name
)
SELECT DISTINCT
    TRIM(region)
FROM source.customers
WHERE region IS NOT NULL
  AND TRIM(region) <> ''

ON CONFLICT (region_name)
DO NOTHING;
"""


def load_dim_region(conn):

    with conn.cursor() as cur:

        cur.execute(LOAD_REGION_SQL)

        changed = cur.rowcount

    logger.info(
        "地区维度新增：%s",
        changed
    )

    return changed


# ============================================================
# 4. 客户维度装载
# ============================================================

LOAD_CUSTOMER_SQL = """
INSERT INTO dwd.dim_customer (
    customer_id,
    region_key
)
SELECT
    c.customer_id::VARCHAR(64),
    r.region_key
FROM source.customers AS c

LEFT JOIN dwd.dim_region AS r
    ON TRIM(c.region) = r.region_name

WHERE c.customer_id IS NOT NULL

ON CONFLICT (customer_id)
DO UPDATE SET

    region_key = EXCLUDED.region_key,

    updated_at = CURRENT_TIMESTAMP

WHERE dwd.dim_customer.region_key
      IS DISTINCT FROM EXCLUDED.region_key;
"""


def load_dim_customer(conn):

    with conn.cursor() as cur:

        cur.execute(LOAD_CUSTOMER_SQL)

        changed = cur.rowcount

    logger.info(
        "客户维度新增或更新：%s",
        changed
    )

    return changed


# ============================================================
# 5. 数据质量检查
# ============================================================

def validate_dimensions(conn):

    queries = {

        "地区总数": """
            SELECT COUNT(*)
            FROM dwd.dim_region
        """,

        "客户总数": """
            SELECT COUNT(*)
            FROM dwd.dim_customer
        """,

        "日期总数": """
            SELECT COUNT(*)
            FROM dwd.dim_date
        """,

        "客户业务键重复数": """
            SELECT COUNT(*)
            FROM (
                SELECT customer_id
                FROM dwd.dim_customer
                GROUP BY customer_id
                HAVING COUNT(*) > 1
            ) AS t
        """,

        "客户地区缺失数": """
            SELECT COUNT(*)
            FROM dwd.dim_customer
            WHERE region_key IS NULL
        """
    }

    results = {}

    with conn.cursor() as cur:

        for name, sql in queries.items():

            cur.execute(sql)

            results[name] = cur.fetchone()[0]

    logger.info("========== 维度检查 ==========")

    for name, value in results.items():
        logger.info("%s：%s", name, value)

    if results["客户业务键重复数"] != 0:
        raise ValueError("客户维度存在重复业务键")

    if results["客户地区缺失数"] != 0:
        raise ValueError(
            "存在未映射地区的客户，请检查源数据"
        )

    return results


# ============================================================
# 6. 主流程
# ============================================================

def main():

    logger.info("D15 维度装载开始")

    with get_connection() as conn:

        try:

            load_dim_region(conn)

            load_dim_customer(conn)

            validate_dimensions(conn)

            conn.commit()

        except Exception:

            conn.rollback()

            logger.exception("维度装载失败")

            raise

    logger.info("D15 维度装载成功")


if __name__ == "__main__":
    main()
