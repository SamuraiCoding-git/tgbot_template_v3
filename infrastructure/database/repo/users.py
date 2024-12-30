import json
import logging
from typing import Optional, List, Sequence

from sqlalchemy import select, update, func, desc
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.sql.expression import literal

from infrastructure.database.models import User, Referral
from infrastructure.database.redis_client import RedisClient
from infrastructure.database.repo.base import BaseRepo


class UserRepo(BaseRepo):
    def __init__(self, session, redis_client: RedisClient):
        super().__init__(session)
        self.redis_client = redis_client
        self.logger = logging.getLogger(__name__)

    async def create_user(self, user_id: int, language: str, referred_by: Optional[int] = None,
                          reward_type: Optional[int] = 1) -> Optional[User]:
        try:
            async with self.session.begin():
                insert_user_stmt = (
                    insert(User)
                    .values(user_id=user_id, language=language)
                    .on_conflict_do_update(
                        index_elements=[User.user_id],
                        set_=dict(language=language),
                    )
                    .returning(User)
                )
                result = await self.session.execute(insert_user_stmt)
                user = result.scalar_one()

                insert_referral_stmt = (
                    insert(Referral)
                    .values(referral_id=user_id, referred_by=referred_by, reward_type=reward_type)
                )
                await self.session.execute(insert_referral_stmt)

                # Update Redis cache directly
                await self.redis_client.hset_dict(
                    f"user:{user_id}",
                    {
                        "user_id": user.user_id,
                        "language": user.language,
                        "balance": user.balance
                    }
                )

                return user

        except Exception as e:
            self.logger.error(f"Error creating user {user_id} and referral: {e}")
            return None

    async def select_user(self, user_id: int) -> Optional[User]:
        try:
            cached_user = await self.redis_client.redis.hgetall(f"user:{user_id}")
            if cached_user:
                return User(user_id=int(cached_user["user_id"]),
                            language=cached_user["language"],
                            balance=int(cached_user["balance"]))

            query = select(User).where(User.user_id == literal(user_id))
            result = await self.session.execute(query)
            user = result.scalar_one_or_none()

            if user:
                await self.redis_client.hset_dict(
                    f"user:{user_id}",
                    {
                        "user_id": user.user_id,
                        "language": user.language,
                        "balance": user.balance
                    }
                )

            return user
        except Exception as e:
            self.logger.error(f"Failed to select user {user_id}: {e}")
            return None

    async def update_user(self, user_id: int, language: Optional[str] = None, balance: Optional[int] = None) -> \
    Optional[User]:
        try:
            # Retrieve the current user details including the balance
            user = await self.select_user(user_id)

            if user is None:
                self.logger.error(f"User {user_id} not found when attempting to update balance.")
                return None

            # If a new balance is provided, add it to the existing balance
            if balance is not None:
                balance += user.balance

            update_stmt = update(User).where(User.user_id == user_id)

            if language is not None:
                update_stmt = update_stmt.values(language=language)
            if balance is not None:
                update_stmt = update_stmt.values(balance=balance)

            result = await self.session.execute(update_stmt.returning(User))
            await self.session.commit()

            updated_user = result.scalar_one_or_none()

            if updated_user:
                await self.redis_client.hset_dict(
                    f"user:{user_id}",
                    {
                        "user_id": updated_user.user_id,
                        "language": updated_user.language,
                        "balance": updated_user.balance
                    }
                )

            return updated_user
        except Exception as e:
            self.logger.error(f"Error updating user {user_id}: {e}")
            return None

    async def select_leaderboard(self, user_id: int) -> dict:
        try:
            leaderboard_cache_key = "leaderboard:top5"
            user_rank_cache_key = f"user:{user_id}:rank"

            cached_leaderboard = await self.redis_client.redis.get(leaderboard_cache_key)
            leaderboard = json.loads(cached_leaderboard) if cached_leaderboard else None

            if leaderboard:
                user_rank = next((row['place'] for row in leaderboard if row['user_id'] == user_id), None)
            else:
                top_users_query = (
                    select(User.user_id, User.balance)
                    .order_by(desc(User.balance))
                    .limit(5)
                )
                top_users_result = await self.session.execute(top_users_query)
                top_users = top_users_result.fetchall()

                leaderboard = [
                    {
                        "user_id": row.user_id,
                        "place": idx + 1,
                        "balance": row.balance
                    }
                    for idx, row in enumerate(top_users)
                ]

                async with self.redis_client.redis.pipeline() as pipe:
                    pipe.setex(leaderboard_cache_key, 86400, json.dumps(leaderboard))
                    await pipe.execute()

                user_rank = next((row['place'] for row in leaderboard if row['user_id'] == user_id), None)

            if user_rank is None:
                cached_user_rank = await self.redis_client.redis.get(user_rank_cache_key)
                if cached_user_rank:
                    user_rank = int(cached_user_rank)
                else:
                    rank_query = (
                        select(func.count())
                        .select_from(User)
                        .where(User.balance > (select(User.balance).where(User.user_id == user_id).scalar_subquery()))
                    )
                    user_rank = (await self.session.execute(rank_query)).scalar() + 1
                    await self.redis_client.redis.setex(user_rank_cache_key, 86400, user_rank)

            return {
                "leaderboard": leaderboard,
                "place": user_rank
            }
        except Exception as e:
            self.logger.error(f"Error selecting leaderboard for user {user_id}: {e}")
            return {"leaderboard": [], "place": None}

    async def batch_create_users(self, users: List[dict]) -> None:
        try:
            await self.session.execute(
                insert(User),
                users
            )
            await self.session.commit()

            async with self.redis_client.redis.pipeline() as pipe:
                for user in users:
                    await self.redis_client.hset_dict(
                        f"user:{user['user_id']}",
                        {
                            "user_id": user['user_id'],
                            "language": user['language'],
                            "balance": user['balance']
                        }
                    )
                await pipe.execute()

        except Exception as e:
            self.logger.error(f"Error batch creating users: {e}")

    async def get_all_users(self) -> Sequence[User]:
        """
        Retrieves a list of all users in the database.

        :return: A list of User objects.
        """
        try:
            query = select(User)
            result = await self.session.execute(query)
            users = result.scalars().all()
            return users
        except SQLAlchemyError as e:
            self.logger.error(f"Error retrieving all users: {e}")
            return []
