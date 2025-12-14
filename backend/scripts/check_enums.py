"""检查数据库中的枚举类型"""

import asyncio

import asyncpg


async def check_enums():
    conn = await asyncpg.connect(
        host="localhost",
        port=5432,
        user="knowbase",
        password="knowbase123",
        database="knowbase",
    )

    try:
        # 查询所有枚举类型
        enums = await conn.fetch(
            """
            SELECT t.typname, e.enumlabel 
            FROM pg_type t 
            JOIN pg_enum e ON t.oid = e.enumtypid 
            ORDER BY t.typname, e.enumsortorder;
        """
        )

        print("=" * 60)
        print("数据库中的枚举类型:")
        print("=" * 60)

        current_type = None
        for row in enums:
            if current_type != row["typname"]:
                current_type = row["typname"]
                print(f"\n{current_type}:")
            print(f"  - {row['enumlabel']}")

        if not enums:
            print("未找到任何枚举类型")

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(check_enums())
