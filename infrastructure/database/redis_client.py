import redis.asyncio as aioredis

class RedisClient:
    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self.redis = None

    async def connect(self):
        self.redis = aioredis.from_url(self.redis_url, decode_responses=True)

    async def close(self):
        await self.redis.close()

    async def hset_dict(self, key: str, mapping: dict):
        """
        Sets multiple fields in a hash stored at key.
        :param key: The key of the hash.
        :param mapping: A dictionary of field-value pairs to set in the hash.
        """
        await self.redis.hset(key, mapping=mapping)
