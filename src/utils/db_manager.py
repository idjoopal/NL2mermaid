"""
DB Manager

PostgreSQL 및 MariaDB 연결을 관리하고, DDL 추출 및 SELECT 쿼리 실행 기능을 제공합니다.

사용법:
    db = DBManager(
        db_type="postgresql",
        host="localhost",
        port=5432,
        name="mydb",
        user="admin",
        password="secret"
    )
    await db.connect()
    result = await db.execute_select("SELECT * FROM users LIMIT 10")
    ddl = await db.get_ddl("users")
    await db.disconnect()
"""
from typing import Any, Dict, List, Optional

from src.utils.logger import get_logger

logger = get_logger("db_manager")


class DBManager:
    """데이터베이스 연결 및 쿼리 실행 매니저"""

    SUPPORTED_DB_TYPES = ("postgresql", "mariadb")

    def __init__(
        self,
        db_type: str,
        host: str,
        port: int,
        name: str,
        user: str,
        password: str,
    ):
        """
        Args:
            db_type: 데이터베이스 종류 ("postgresql" | "mariadb")
            host: DB 호스트
            port: DB 포트
            name: 데이터베이스 이름
            user: 접속 사용자
            password: 접속 비밀번호
        """
        self.db_type = db_type.lower()
        if self.db_type not in self.SUPPORTED_DB_TYPES:
            raise ValueError(
                f"지원하지 않는 DB 종류입니다: {self.db_type}. "
                f"지원 목록: {self.SUPPORTED_DB_TYPES}"
            )

        self.host = host
        self.port = port
        self.name = name
        self.user = user
        self.password = password

        self._connection = None
        self._pool = None

    @property
    def connected(self) -> bool:
        """DB 연결 상태 확인"""
        return self._pool is not None

    # ──────────────────────────────────────────────
    # 연결 / 해제
    # ──────────────────────────────────────────────
    async def connect(self) -> None:
        """데이터베이스에 연결합니다."""
        if self.connected:
            logger.info("[DB] 이미 연결되어 있습니다.")
            return

        logger.info(f"[DB] {self.db_type} 연결 시작 — {self.host}:{self.port}/{self.name}")

        if self.db_type == "postgresql":
            await self._connect_postgresql()
        elif self.db_type == "mariadb":
            await self._connect_mariadb()

        logger.info(f"[DB] {self.db_type} 연결 완료")

    async def disconnect(self) -> None:
        """데이터베이스 연결을 종료합니다."""
        if not self.connected:
            return

        logger.info(f"[DB] {self.db_type} 연결 종료")

        if self.db_type == "postgresql":
            await self._pool.close()
        elif self.db_type == "mariadb":
            self._pool.close()
            await self._pool.wait_closed()

        self._pool = None

    # ──────────────────────────────────────────────
    # DDL 추출
    # ──────────────────────────────────────────────
    async def get_ddl(self, table_name: str) -> str:
        """
        테이블의 DDL(CREATE TABLE 문)을 반환합니다.

        Args:
            table_name: 테이블 이름

        Returns:
            CREATE TABLE DDL 문자열
        """
        if not self.connected:
            raise ConnectionError("DB에 연결되어 있지 않습니다. connect()를 먼저 호출하세요.")

        logger.info(f"[DB] DDL 추출 — 테이블: {table_name}")

        if self.db_type == "postgresql":
            return await self._get_ddl_postgresql(table_name)
        elif self.db_type == "mariadb":
            return await self._get_ddl_mariadb(table_name)

    # ──────────────────────────────────────────────
    # SELECT 쿼리 실행
    # ──────────────────────────────────────────────
    async def execute_select(
        self, query: str, params: Optional[tuple] = None
    ) -> List[Dict[str, Any]]:
        """
        SELECT 쿼리를 실행하고 결과를 딕셔너리 리스트로 반환합니다.

        Args:
            query: 실행할 SELECT SQL 쿼리
            params: 바인드 파라미터 (선택)

        Returns:
            [{"column1": value1, "column2": value2, ...}, ...] 형태의 결과
        """
        if not self.connected:
            raise ConnectionError("DB에 연결되어 있지 않습니다. connect()를 먼저 호출하세요.")

        logger.info(f"[DB] SELECT 실행 — {query[:100]}{'...' if len(query) > 100 else ''}")

        if self.db_type == "postgresql":
            return await self._execute_select_postgresql(query, params)
        elif self.db_type == "mariadb":
            return await self._execute_select_mariadb(query, params)

    # ══════════════════════════════════════════════
    # PostgreSQL 내부 구현
    # ══════════════════════════════════════════════
    async def _connect_postgresql(self) -> None:
        import asyncpg

        self._pool = await asyncpg.create_pool(
            host=self.host,
            port=self.port,
            database=self.name,
            user=self.user,
            password=self.password,
            min_size=1,
            max_size=5,
        )

    async def _get_ddl_postgresql(self, table_name: str) -> str:
        """
        PostgreSQL의 information_schema를 이용해 DDL을 조합합니다.
        """
        query = """
            SELECT
                c.column_name,
                c.data_type,
                c.character_maximum_length,
                c.is_nullable,
                c.column_default,
                tc.constraint_type
            FROM information_schema.columns c
            LEFT JOIN information_schema.key_column_usage kcu
                ON c.table_name = kcu.table_name
                AND c.column_name = kcu.column_name
                AND c.table_schema = kcu.table_schema
            LEFT JOIN information_schema.table_constraints tc
                ON kcu.constraint_name = tc.constraint_name
                AND kcu.table_schema = tc.table_schema
            WHERE c.table_name = $1
                AND c.table_schema = 'public'
            ORDER BY c.ordinal_position
        """
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(query, table_name)

        if not rows:
            return f"-- 테이블 '{table_name}'을 찾을 수 없습니다."

        columns = []
        for row in rows:
            col_def = f"    {row['column_name']} {row['data_type']}"
            if row["character_maximum_length"]:
                col_def += f"({row['character_maximum_length']})"
            if row["is_nullable"] == "NO":
                col_def += " NOT NULL"
            if row["column_default"]:
                col_def += f" DEFAULT {row['column_default']}"
            if row["constraint_type"] == "PRIMARY KEY":
                col_def += " PRIMARY KEY"
            columns.append(col_def)

        ddl = f"CREATE TABLE {table_name} (\n" + ",\n".join(columns) + "\n);"
        return ddl

    async def _execute_select_postgresql(
        self, query: str, params: Optional[tuple] = None
    ) -> List[Dict[str, Any]]:
        async with self._pool.acquire() as conn:
            if params:
                rows = await conn.fetch(query, *params)
            else:
                rows = await conn.fetch(query)
            return [dict(row) for row in rows]

    # ══════════════════════════════════════════════
    # MariaDB 내부 구현
    # ══════════════════════════════════════════════
    async def _connect_mariadb(self) -> None:
        import aiomysql

        self._pool = await aiomysql.create_pool(
            host=self.host,
            port=self.port,
            db=self.name,
            user=self.user,
            password=self.password,
            minsize=1,
            maxsize=5,
            autocommit=True,
        )

    async def _get_ddl_mariadb(self, table_name: str) -> str:
        """
        MariaDB의 SHOW CREATE TABLE을 이용해 DDL을 가져옵니다.
        """
        query = f"SHOW CREATE TABLE `{table_name}`"
        async with self._pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query)
                row = await cur.fetchone()
                if row:
                    return row[1]
                return f"-- 테이블 '{table_name}'을 찾을 수 없습니다."

    async def _execute_select_mariadb(
        self, query: str, params: Optional[tuple] = None
    ) -> List[Dict[str, Any]]:
        import aiomysql

        async with self._pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                if params:
                    await cur.execute(query, params)
                else:
                    await cur.execute(query)
                rows = await cur.fetchall()
                return [dict(row) for row in rows]
