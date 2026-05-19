"""Notification service for WebSocket-based in-app notifications.

No email, no SMS, no external APIs.
All notifications stored in DB and pushed via WebSocket.
"""

import logging
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc

from backend.models.notification import Notification, NotificationType
from backend.models.user import User
from backend.schemas.notification import (
    NotificationCreate,
    NotificationResponse,
    NotificationList,
)

logger = logging.getLogger(__name__)


class NotificationService:
    """Service for managing in-app WebSocket notifications."""

    @staticmethod
    async def create_notification(
        db: AsyncSession,
        recipient_id: int,
        title: str,
        message: str,
        notification_type: str,
    ) -> NotificationResponse:
        """Create and store notification.

        Args:
            db: Database session.
            recipient_id: User ID receiving notification.
            title: Notification title.
            message: Notification message body.
            notification_type: Type (zone_drop, reminder, etc.).

        Returns:
            NotificationResponse.
        """
        try:
            notification = Notification(
                recipient_id=recipient_id,
                title=title,
                message=message,
                type=notification_type,
                is_read=False,
                created_at=datetime.utcnow(),
            )
            db.add(notification)
            await db.commit()
            await db.refresh(notification)

            logger.info(
                f"Created notification {notification.id} for user {recipient_id}: "
                f"{notification_type}"
            )
            return NotificationResponse.from_orm(notification)

        except Exception as e:
            await db.rollback()
            logger.error(f"Error creating notification: {e}")
            raise

    @staticmethod
    async def create_bulk_notifications(
        db: AsyncSession,
        recipient_ids: list[int],
        title: str,
        message: str,
        notification_type: str,
    ) -> list[NotificationResponse]:
        """Create notifications for multiple users.

        Args:
            db: Database session.
            recipient_ids: List of user IDs.
            title: Notification title.
            message: Notification message body.
            notification_type: Type of notification.

        Returns:
            List of NotificationResponse.
        """
        try:
            notifications = [
                Notification(
                    recipient_id=rid,
                    title=title,
                    message=message,
                    type=notification_type,
                    is_read=False,
                    created_at=datetime.utcnow(),
                )
                for rid in recipient_ids
            ]
            db.add_all(notifications)
            await db.commit()

            logger.info(
                f"Created {len(notifications)} notifications of type {notification_type}"
            )
            return [
                NotificationResponse.from_orm(n) for n in notifications
            ]

        except Exception as e:
            await db.rollback()
            logger.error(f"Error creating bulk notifications: {e}")
            raise

    @staticmethod
    async def get_user_notifications(
        db: AsyncSession,
        user_id: int,
        limit: int = 50,
        offset: int = 0,
    ) -> NotificationList:
        """Get user's notifications (most recent first).

        Args:
            db: Database session.
            user_id: User ID.
            limit: Max results.
            offset: Pagination offset.

        Returns:
            NotificationList with pagination.
        """
        try:
            # Count total
            count_result = await db.execute(
                select(func.count(Notification.id)).filter(
                    Notification.recipient_id == user_id
                )
            )
            total = count_result.scalar() or 0

            # Get unread count
            unread_result = await db.execute(
                select(func.count(Notification.id)).filter(
                    and_(
                        Notification.recipient_id == user_id,
                        Notification.is_read == False,
                    )
                )
            )
            unread_count = unread_result.scalar() or 0

            # Get notifications
            query = (
                select(Notification)
                .filter(Notification.recipient_id == user_id)
                .order_by(desc(Notification.created_at))
                .limit(limit)
                .offset(offset)
            )
            result = await db.execute(query)
            notifications = result.scalars().all()

            return NotificationList(
                notifications=[
                    NotificationResponse.from_orm(n) for n in notifications
                ],
                unread_count=unread_count,
                total_count=total,
            )

        except Exception as e:
            logger.error(f"Error getting notifications for user {user_id}: {e}")
            raise

    @staticmethod
    async def mark_as_read(
        db: AsyncSession,
        notification_id: int,
    ) -> NotificationResponse:
        """Mark notification as read.

        Args:
            db: Database session.
            notification_id: Notification ID.

        Returns:
            Updated NotificationResponse.
        """
        try:
            query = select(Notification).filter(
                Notification.id == notification_id
            )
            result = await db.execute(query)
            notification = result.scalar_one()

            notification.is_read = True
            await db.commit()
            await db.refresh(notification)

            return NotificationResponse.from_orm(notification)

        except Exception as e:
            await db.rollback()
            logger.error(f"Error marking notification {notification_id} as read: {e}")
            raise

    @staticmethod
    async def mark_all_as_read(
        db: AsyncSession,
        user_id: int,
    ) -> int:
        """Mark all user's notifications as read.

        Args:
            db: Database session.
            user_id: User ID.

        Returns:
            Number of notifications marked as read.
        """
        try:
            query = (
                select(Notification)
                .filter(
                    and_(
                        Notification.recipient_id == user_id,
                        Notification.is_read == False,
                    )
                )
            )
            result = await db.execute(query)
            notifications = result.scalars().all()

            for notification in notifications:
                notification.is_read = True

            await db.commit()

            count = len(notifications)
            logger.info(f"Marked {count} notifications as read for user {user_id}")
            return count

        except Exception as e:
            await db.rollback()
            logger.error(
                f"Error marking all notifications as read for user {user_id}: {e}"
            )
            raise

    @staticmethod
    async def delete_notification(
        db: AsyncSession,
        notification_id: int,
    ) -> bool:
        """Delete a notification.

        Args:
            db: Database session.
            notification_id: Notification ID.

        Returns:
            True if deleted, False if not found.
        """
        try:
            query = select(Notification).filter(
                Notification.id == notification_id
            )
            result = await db.execute(query)
            notification = result.scalar()

            if not notification:
                return False

            await db.delete(notification)
            await db.commit()

            logger.info(f"Deleted notification {notification_id}")
            return True

        except Exception as e:
            await db.rollback()
            logger.error(f"Error deleting notification {notification_id}: {e}")
            raise


from sqlalchemy import func
