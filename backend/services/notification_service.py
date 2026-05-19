"""Notification service for in-app WebSocket notifications.

No email, no SMS — pure WebSocket only.
Notifications are persisted to DB and sent to connected clients.
"""

import logging
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from backend.models.notification import Notification
from backend.schemas.notification import (
    NotificationCreate,
    NotificationResponse,
    NotificationList,
)

logger = logging.getLogger(__name__)

# In-memory store of WebSocket connections: {user_id: set of WebSocket connections}
_active_connections: dict[int, set] = {}


class NotificationService:
    """Service for managing in-app notifications."""

    @staticmethod
    async def create_notification(
        db: AsyncSession,
        recipient_id: int,
        title: str,
        message: str,
        notification_type: str,
    ) -> NotificationResponse:
        """Create and persist a notification.

        Args:
            db: Database session.
            recipient_id: User ID of recipient.
            title: Notification title.
            message: Notification message.
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
                f"Notification created for user {recipient_id}: {title}"
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
        """Create multiple notifications at once.

        Args:
            db: Database session.
            recipient_ids: List of user IDs.
            title: Notification title.
            message: Notification message.
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

            results = []
            for notif in notifications:
                await db.refresh(notif)
                results.append(NotificationResponse.from_orm(notif))

            logger.info(
                f"Bulk notification created for {len(recipient_ids)} users: {title}"
            )
            return results

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
        """Get notifications for a user.

        Args:
            db: Database session.
            user_id: User ID.
            limit: Max results.
            offset: Pagination offset.

        Returns:
            NotificationList with unread count.
        """
        try:
            # Get total count
            total_result = await db.execute(
                select(func.count(Notification.id)).filter(
                    Notification.recipient_id == user_id
                )
            )
            total_count = total_result.scalar() or 0

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

            # Get paginated notifications (newest first)
            notifs_result = await db.execute(
                select(Notification)
                .filter(Notification.recipient_id == user_id)
                .order_by(Notification.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
            notifications = notifs_result.scalars().all()

            return NotificationList(
                notifications=[
                    NotificationResponse.from_orm(n) for n in notifications
                ],
                unread_count=unread_count,
                total_count=total_count,
            )

        except Exception as e:
            logger.error(f"Error getting notifications for user {user_id}: {e}")
            raise

    @staticmethod
    async def mark_notification_read(
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
            notif_result = await db.execute(
                select(Notification).filter(Notification.id == notification_id)
            )
            notification = notif_result.scalar_one()
            notification.is_read = True
            await db.commit()
            await db.refresh(notification)

            return NotificationResponse.from_orm(notification)

        except Exception as e:
            await db.rollback()
            logger.error(f"Error marking notification read: {e}")
            raise

    @staticmethod
    async def mark_all_read(
        db: AsyncSession,
        user_id: int,
    ) -> int:
        """Mark all notifications for user as read.

        Args:
            db: Database session.
            user_id: User ID.

        Returns:
            Number of notifications marked read.
        """
        try:
            result = await db.execute(
                select(Notification).filter(
                    and_(
                        Notification.recipient_id == user_id,
                        Notification.is_read == False,
                    )
                )
            )
            notifications = result.scalars().all()

            for notif in notifications:
                notif.is_read = True

            await db.commit()
            logger.info(f"Marked {len(notifications)} notifications read for user {user_id}")
            return len(notifications)

        except Exception as e:
            await db.rollback()
            logger.error(f"Error marking all read for user {user_id}: {e}")
            raise

    @staticmethod
    def add_connection(user_id: int, websocket):
        """Register a WebSocket connection.

        Args:
            user_id: User ID.
            websocket: WebSocket connection object.
        """
        if user_id not in _active_connections:
            _active_connections[user_id] = set()
        _active_connections[user_id].add(websocket)
        logger.info(f"WebSocket connected for user {user_id}")

    @staticmethod
    def remove_connection(user_id: int, websocket):
        """Unregister a WebSocket connection.

        Args:
            user_id: User ID.
            websocket: WebSocket connection object.
        """
        if user_id in _active_connections:
            _active_connections[user_id].discard(websocket)
            if not _active_connections[user_id]:
                del _active_connections[user_id]
        logger.info(f"WebSocket disconnected for user {user_id}")

    @staticmethod
    async def broadcast_to_user(
        user_id: int,
        message: dict,
    ) -> int:
        """Broadcast message to all WebSocket connections of a user.

        Args:
            user_id: User ID.
            message: Message dict to send.

        Returns:
            Number of connections message was sent to.
        """
        connections = _active_connections.get(user_id, set())
        disconnected = set()

        for websocket in connections:
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.warning(f"Error sending to WebSocket: {e}")
                disconnected.add(websocket)

        # Clean up disconnected
        for ws in disconnected:
            NotificationService.remove_connection(user_id, ws)

        return len(connections) - len(disconnected)

    @staticmethod
    async def broadcast_to_users(
        user_ids: list[int],
        message: dict,
    ) -> dict[int, int]:
        """Broadcast message to multiple users.

        Args:
            user_ids: List of user IDs.
            message: Message dict to send.

        Returns:
            Dict of {user_id: connections_sent}.
        """
        results = {}
        for uid in user_ids:
            count = await NotificationService.broadcast_to_user(uid, message)
            results[uid] = count
        return results


from sqlalchemy import func
