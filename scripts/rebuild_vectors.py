"""Safely rebuild all Chroma POI collections from PostgreSQL."""

import argparse
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import engine
from app.services.vector.rebuild import rebuild_vector_index


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="从 PostgreSQL 安全全量重建 Chroma 向量库",
    )
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument(
        "--allow-pseudo",
        action="store_true",
        help="允许模型加载失败时使用伪 embedding",
    )
    args = parser.parse_args()

    print("=" * 50)
    print("AI Travel Planner - Chroma 安全全量重建")
    print("=" * 50)
    try:
        result = await rebuild_vector_index(
            batch_size=args.batch_size,
            allow_pseudo=args.allow_pseudo,
        )
    finally:
        await engine.dispose()

    print(f"\n完成：{result.active_dir}")
    print(f"集合数量：{result.counts}")
    if result.backup_dir is not None:
        print(f"旧索引备份：{result.backup_dir}")


if __name__ == "__main__":
    event_loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(event_loop)
        event_loop.run_until_complete(main())
    finally:
        event_loop.close()
        asyncio.set_event_loop(None)
