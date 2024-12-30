import logging
from typing import Optional, Dict, Any, Sequence

from sqlalchemy import select, func, Row, RowMapping

from infrastructure.database.models import Referral, User
from infrastructure.database.redis_client import RedisClient
from infrastructure.database.repo.base import BaseRepo


class ReferralsRepo(BaseRepo):
    def __init__(self, session, redis_client: RedisClient):
        super().__init__(session)
        self.redis_client = redis_client
        self.logger = logging.getLogger(__name__)

    async def get_referrals_by_user(self, referred_by: int) -> Sequence[Row[Any] | RowMapping | Any]:
        try:
            cache_key = f"referrals_by_user:{referred_by}"
            cached_referrals = await self.redis_client.redis.hgetall(cache_key)

            if cached_referrals:
                return [Referral(referral_id=int(cached_referrals[f"referral_id:{i}"]),
                                 referred_by=referred_by,
                                 reward_type=int(cached_referrals[f"reward_type:{i}"]))
                        for i in range(len(cached_referrals) // 3)]

            query = select(Referral).where(Referral.referred_by == referred_by)
            result = await self.session.execute(query)
            referrals = result.scalars().all()

            if referrals:
                referral_data = {}
                for i, referral in enumerate(referrals):
                    referral_data[f"referral_id:{i}"] = referral.referral_id
                    referral_data[f"reward_type:{i}"] = referral.reward_type

                await self.redis_client.redis.hset(cache_key, mapping=referral_data)
                await self.redis_client.redis.expire(cache_key, 86400)

            return referrals
        except Exception as e:
            self.logger.error(f"Error retrieving referrals for user {referred_by}: {e}")
            return []

    async def count_referrals_by_user(self, referred_by: int) -> Dict[str, int]:
        try:
            cache_key = f"referral_breakdown:{referred_by}"
            cached_counts = await self.redis_client.redis.hgetall(cache_key)

            if cached_counts:
                return {
                    "first_referrals": int(cached_counts.get("first_referrals", 0)),
                    "second_referrals": int(cached_counts.get("second_referrals", 0))
                }

            first_referrals_count = await self._count_direct_referrals(referred_by)

            first_referrals_ids = await self._get_direct_referrals_ids(referred_by)

            if not first_referrals_ids:
                second_referrals_count = 0
            else:
                second_referrals_count = await self._count_second_referrals(first_referrals_ids)

            await self.redis_client.redis.hset(cache_key, mapping={
                "first_referrals": first_referrals_count,
                "second_referrals": second_referrals_count
            })
            await self.redis_client.redis.expire(cache_key, 86400)

            return {
                "first_referrals": first_referrals_count,
                "second_referrals": second_referrals_count
            }
        except Exception as e:
            self.logger.error(f"Error counting referrals for user {referred_by}: {e}")
            return {
                "first_referrals": 0,
                "second_referrals": 0
            }

    async def _count_direct_referrals(self, referred_by: int) -> int:
        query = select(func.count()).where(Referral.referred_by == referred_by)
        result = await self.session.execute(query)
        return result.scalar()

    async def _get_direct_referrals_ids(self, referred_by: int) -> Sequence[int]:
        query = select(Referral.referral_id).where(Referral.referred_by == referred_by)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def _count_second_referrals(self, first_referrals_ids: Sequence[int]) -> int:
        query = select(func.count()).where(Referral.referred_by.in_(first_referrals_ids))
        result = await self.session.execute(query)
        return result.scalar()

    async def get_referral(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Retrieves a referral by the referred user's ID along with the referrer's language.

        :param user_id: The ID of the referred user.
        :return: A dictionary containing the Referral object and the referrer's language, or None if not found.
        """
        try:
            cache_key = f"referral:{user_id}"
            cached_referral = await self.redis_client.redis.hgetall(cache_key)

            # Check if we have valid cached data
            if cached_referral and all(cached_referral.get(key) not in (None, 'None', '') for key in ["referral_id", "referred_by", "reward_type", "language"]):
                return {
                    "referral": Referral(
                        referral_id=int(cached_referral["referral_id"]),
                        referred_by=int(cached_referral["referred_by"]) if cached_referral["referred_by"] else None,
                        reward_type=int(cached_referral["reward_type"])
                    ),
                    "language": cached_referral["language"] or "en"  # Default to 'en' if language is None or empty
                }

            # If not cached, query the database
            stmt = (
                select(Referral, User.language)
                .outerjoin(User, Referral.referral_id == User.user_id)
                .where(Referral.referral_id == user_id)
            )
            compiled_stmt = stmt.compile(compile_kwargs={"literal_binds": True})
            print(str(compiled_stmt))
            result = await self.session.execute(stmt)
            row = result.first()

            if row:
                print(row)
                referral, language = row
                referral_dict = {
                    "referral": referral,
                    "language": language or "en"  # Default to 'en' if language is None
                }

                # Cache the referral and language data
                await self.redis_client.redis.hset(cache_key, mapping={
                    "referral_id": str(referral.referral_id),
                    "referred_by": str(referral.referred_by) if referral.referred_by is not None else '',
                    "reward_type": str(referral.reward_type) if referral.reward_type is not None else '',
                    "language": language or 'en'
                })
                await self.redis_client.redis.expire(cache_key, 86400)  # Set expiry to 24 hours

                return referral_dict

            return None

        except Exception as e:
            self.logger.error(f"Error retrieving referral for user {user_id}: {e}")
            return None
