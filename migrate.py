"""为 live 表添加 slug 列并填充现有数据。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from db import init_db
from utils import live_slug

DB_PATH = sys.argv[1] if len(sys.argv) > 1 else "asoul.db"

conn = init_db(DB_PATH)

try:
    conn.execute("ALTER TABLE live ADD COLUMN slug TEXT NOT NULL DEFAULT ''")
    print("已添加 slug 列")
except Exception:
    print("slug 列已存在，跳过")

rows = conn.execute("SELECT id, start_time, title FROM live WHERE slug = ''").fetchall()
for row_id, start_time, title in rows:
    slug = live_slug(start_time, title)
    conn.execute("UPDATE live SET slug = ? WHERE id = ?", (slug, row_id))

conn.commit()
print(f"已更新 {len(rows)} 条记录")
conn.close()
