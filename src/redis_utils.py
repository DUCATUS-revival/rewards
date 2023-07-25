# flake8: noqa
import redis


class RedisClient:
    def __init__(self) -> None:
        self.pool = redis.ConnectionPool(
            host="redis", port=6379, db=0, decode_responses=True
        )

    def set_connection(self) -> None:
        self._conn = redis.Redis(connection_pool=self.pool)

    @property
    def connection(self) -> "redis.Redis":
        if not hasattr(self, "_conn"):
            self.set_connection()
        return self._conn

    @classmethod
    def get(cls, key: str) -> str:
        connection = cls().connection
        return connection.get(key)

    @classmethod
    def expiretime(cls, key: str) -> int:
        connection = cls().connection
        return connection.expiretime(key)

    @classmethod
    def increase(cls, key: str) -> int:
        connection = cls().connection
        return connection.incrby(key)

    @classmethod
    def set(cls, key: str, value: any, expire: int = None) -> None:  # noqa A003
        connection = cls().connection
        connection.set(key, value, ex=expire)

    @classmethod
    def delete(cls, key: str) -> None:
        connection = cls().connection
        connection.delete(key)

    @classmethod
    def get_and_del(cls, key: str) -> None:
        connection = cls().connection
        message = connection.get(key)
        connection.delete(key)
        return message
