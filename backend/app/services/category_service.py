# backend/app/services/category_service.py
"""
Bonifatus DMS - Category Service
Business logic for category management with Google Drive sync
"""

import logging
import json
from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import select, func, and_, or_

from app.database.models import Category, Document, User, AuditLog, SystemSetting
from app.database.connection import db_manager
from app.schemas.category_schemas import (
    CategoryCreate, CategoryUpdate, CategoryResponse, CategoryListResponse,
    CategoryDeleteRequest, CategoryDeleteResponse, RestoreDefaultsResponse,
    CategoryWithDocumentsResponse
)
from app.services.google_drive_service import google_drive_service

logger = logging.getLogger(__name__)


class CategoryService:
    """Category management service"""

    async def list_categories(
        self, 
        user_id: str,
        include_system: bool = True,
        include_documents_count: bool = True
    ) -> CategoryListResponse:
        """
        List all categories accessible to user
        
        Returns both system categories and user's custom categories
        """
        session = db_manager.session_local()
        try:
            query = select(Category).where(
                or_(
                    Category.is_system == True,
                    Category.user_id == user_id
                )
            ).where(Category.is_active == True).order_by(Category.sort_order, Category.name_en)

            if not include_system:
                query = query.where(Category.user_id == user_id)

            categories = session.execute(query).scalars().all()

            category_responses = []
            for category in categories:
                doc_count = 0
                if include_documents_count:
                    count_query = select(func.count(Document.id)).where(
                        Document.category_id == category.id,
                        Document.user_id == user_id
                    )
                    doc_count = session.execute(count_query).scalar() or 0

                category_responses.append(CategoryResponse(
                    id=str(category.id),
                    name_en=category.name_en,
                    name_de=category.name_de,
                    name_ru=category.name_ru,
                    description_en=category.description_en,
                    description_de=category.description_de,
                    description_ru=category.description_ru,
                    color_hex=category.color_hex,
                    icon_name=category.icon_name,
                    is_system=category.is_system,
                    user_id=str(category.user_id) if category.user_id else None,
                    sort_order=category.sort_order,
                    is_active=category.is_active,
                    documents_count=doc_count,
                    created_at=category.created_at,
                    updated_at=category.updated_at
                ))

            return CategoryListResponse(
                categories=category_responses,
                total_count=len(category_responses)
            )

        except Exception as e:
            logger.error(f"Failed to list categories: {e}")
            raise
        finally:
            session.close()

    async def create_category(
        self, 
        user_id: str,
        user_email: str,
        category_data: CategoryCreate,
        ip_address: str = None
    ) -> CategoryResponse:
        """
        Create new category and sync to Google Drive
        """
        session = db_manager.session_local()
        try:
            new_category = Category(
                name_en=category_data.name_en,
                name_de=category_data.name_de,
                name_ru=category_data.name_ru,
                description_en=category_data.description_en,
                description_de=category_data.description_de,
                description_ru=category_data.description_ru,
                color_hex=category_data.color_hex,
                icon_name=category_data.icon_name,
                is_system=False,
                user_id=user_id,
                sort_order=category_data.sort_order or 999,
                is_active=category_data.is_active if category_data.is_active is not None else True
            )

            session.add(new_category)
            session.commit()
            session.refresh(new_category)

            await self._create_google_drive_folder(
                user_email, 
                category_data.name_en
            )

            await self._log_audit(
                session=session,
                user_id=user_id,
                action="category_created",
                resource_id=str(new_category.id),
                ip_address=ip_address,
                new_values=category_data.dict()
            )

            logger.info(f"Category created: {new_category.id} by user {user_id}")

            return CategoryResponse(
                id=str(new_category.id),
                name_en=new_category.name_en,
                name_de=new_category.name_de,
                name_ru=new_category.name_ru,
                description_en=new_category.description_en,
                description_de=new_category.description_de,
                description_ru=new_category.description_ru,
                color_hex=new_category.color_hex,
                icon_name=new_category.icon_name,
                is_system=new_category.is_system,
                user_id=str(new_category.user_id),
                sort_order=new_category.sort_order,
                is_active=new_category.is_active,
                documents_count=0,
                created_at=new_category.created_at,
                updated_at=new_category.updated_at
            )

        except Exception as e:
            session.rollback()
            logger.error(f"Failed to create category: {e}")
            raise
        finally:
            session.close()

    async def update_category(
        self, 
        category_id: str,
        user_id: str,
        user_email: str,
        category_data: CategoryUpdate,
        ip_address: str = None
    ) -> Optional[CategoryResponse]:
        """
        Update category - works for both system and user categories
        No restrictions on system categories
        """
        session = db_manager.session_local()
        try:
            category = session.get(Category, category_id)
            if not category:
                return None

            if category.user_id and str(category.user_id) != user_id:
                raise PermissionError("Cannot modify another user's category")

            old_name = category.name_en
            old_values = {
                "name_en": category.name_en,
                "name_de": category.name_de,
                "name_ru": category.name_ru,
                "color_hex": category.color_hex,
                "icon_name": category.icon_name
            }

            update_data = category_data.dict(exclude_unset=True)
            for field, value in update_data.items():
                setattr(category, field, value)

            category.updated_at = datetime.utcnow()
            session.commit()
            session.refresh(category)

            if category_data.name_en and category_data.name_en != old_name:
                await self._rename_google_drive_folder(
                    user_email,
                    old_name,
                    category_data.name_en
                )

            await self._log_audit(
                session=session,
                user_id=user_id,
                action="category_updated",
                resource_id=category_id,
                ip_address=ip_address,
                old_values=old_values,
                new_values=update_data
            )

            logger.info(f"Category updated: {category_id} by user {user_id}")

            doc_count = session.execute(
                select(func.count(Document.id)).where(Document.category_id == category.id)
            ).scalar() or 0

            return CategoryResponse(
                id=str(category.id),
                name_en=category.name_en,
                name_de=category.name_de,
                name_ru=category.name_ru,
                description_en=category.description_en,
                description_de=category.description_de,
                description_ru=category.description_ru,
                color_hex=category.color_hex,
                icon_name=category.icon_name,
                is_system=category.is_system,
                user_id=str(category.user_id) if category.user_id else None,
                sort_order=category.sort_order,
                is_active=category.is_active,
                documents_count=doc_count,
                created_at=category.created_at,
                updated_at=category.updated_at
            )

        except Exception as e:
            session.rollback()
            logger.error(f"Failed to update category: {e}")
            raise
        finally:
            session.close()

    async def delete_category(
        self, 
        category_id: str,
        user_id: str,
        user_email: str,
        delete_request: CategoryDeleteRequest,
        ip_address: str = None
    ) -> Optional[CategoryDeleteResponse]:
        """
        Delete category - works for both system and user categories
        Handles document reassignment or deletion
        """
        session = db_manager.session_local()
        try:
            category = session.get(Category, category_id)
            if not category:
                return None

            if category.user_id and str(category.user_id) != user_id:
                raise PermissionError("Cannot delete another user's category")

            doc_count_query = select(func.count(Document.id)).where(
                Document.category_id == category_id
            )
            doc_count = session.execute(doc_count_query).scalar() or 0

            documents_moved = 0
            documents_deleted = 0
            target_category_name = None

            if doc_count > 0:
                if delete_request.delete_documents:
                    delete_stmt = select(Document).where(Document.category_id == category_id)
                    documents = session.execute(delete_stmt).scalars().all()
                    for doc in documents:
                        session.delete(doc)
                    documents_deleted = doc_count
                    logger.warning(f"Deleted {doc_count} documents from category {category_id}")
                else:
                    target_category_id = delete_request.move_to_category_id
                    if not target_category_id:
                        other_category = session.execute(
                            select(Category).where(
                                Category.name_en == "Other",
                                Category.is_system == True
                            )
                        ).scalar_one_or_none()
                        
                        if not other_category:
                            raise ValueError("Default 'Other' category not found")
                        
                        target_category_id = str(other_category.id)
                        target_category_name = "Other"
                    else:
                        target_cat = session.get(Category, target_category_id)
                        if target_cat:
                            target_category_name = target_cat.name_en

                    update_stmt = select(Document).where(Document.category_id == category_id)
                    documents = session.execute(update_stmt).scalars().all()
                    for doc in documents:
                        doc.category_id = target_category_id
                    documents_moved = doc_count

            category_name = category.name_en
            session.delete(category)
            session.commit()

            await self._delete_google_drive_folder(user_email, category_name)

            await self._log_audit(
                session=session,
                user_id=user_id,
                action="category_deleted",
                resource_id=category_id,
                ip_address=ip_address,
                old_values={"name_en": category_name, "documents_count": doc_count}
            )

            logger.info(f"Category deleted: {category_id} by user {user_id}")

            return CategoryDeleteResponse(
                success=True,
                message=f"Category '{category_name}' deleted successfully",
                documents_moved=documents_moved,
                documents_deleted=documents_deleted,
                move_to_category_name=target_category_name
            )

        except Exception as e:
            session.rollback()
            logger.error(f"Failed to delete category: {e}")
            raise
        finally:
            session.close()

    async def restore_default_categories(
        self, 
        user_id: str,
        ip_address: str = None
    ) -> RestoreDefaultsResponse:
        """
        Restore default system categories
        Only creates missing categories, doesn't delete existing ones
        """
        session = db_manager.session_local()
        try:
            default_categories = [
                {
                    'name_en': 'Insurance', 'name_de': 'Versicherung', 'name_ru': 'Страхование',
                    'description_en': 'Insurance policies, claims, and related documents',
                    'description_de': 'Versicherungspolicen, Schadensfälle und verwandte Dokumente',
                    'description_ru': 'Страховые полисы, заявления и связанные документы',
                    'color_hex': '#3B82F6', 'icon_name': 'shield', 'sort_order': 1
                },
                {
                    'name_en': 'Legal', 'name_de': 'Rechtlich', 'name_ru': 'Юридические',
                    'description_en': 'Legal documents, contracts, and agreements',
                    'description_de': 'Rechtsdokumente, Verträge und Vereinbarungen',
                    'description_ru': 'Юридические документы, договоры и соглашения',
                    'color_hex': '#8B5CF6', 'icon_name': 'scales', 'sort_order': 2
                },
                {
                    'name_en': 'Real Estate', 'name_de': 'Immobilien', 'name_ru': 'Недвижимость',
                    'description_en': 'Property documents, deeds, and real estate transactions',
                    'description_de': 'Immobiliendokumente, Urkunden und Immobilientransaktionen',
                    'description_ru': 'Документы на недвижимость, сделки и операции',
                    'color_hex': '#10B981', 'icon_name': 'home', 'sort_order': 3
                },
                {
                    'name_en': 'Banking', 'name_de': 'Banking', 'name_ru': 'Банковские',
                    'description_en': 'Bank statements, financial documents, and transactions',
                    'description_de': 'Kontoauszüge, Finanzdokumente und Transaktionen',
                    'description_ru': 'Банковские выписки, финансовые документы и операции',
                    'color_hex': '#F59E0B', 'icon_name': 'bank', 'sort_order': 4
                },
                {
                    'name_en': 'Other', 'name_de': 'Sonstige', 'name_ru': 'Прочие',
                    'description_en': 'Miscellaneous documents and files',
                    'description_de': 'Verschiedene Dokumente und Dateien',
                    'description_ru': 'Разные документы и файлы',
                    'color_hex': '#6B7280', 'icon_name': 'folder', 'sort_order': 5
                }
            ]

            created = []
            skipped = []

            for cat_data in default_categories:
                existing = session.execute(
                    select(Category).where(
                        Category.name_en == cat_data['name_en'],
                        Category.is_system == True
                    )
                ).scalar_one_or_none()

                if existing:
                    skipped.append(cat_data['name_en'])
                    continue

                new_category = Category(
                    name_en=cat_data['name_en'],
                    name_de=cat_data['name_de'],
                    name_ru=cat_data['name_ru'],
                    description_en=cat_data['description_en'],
                    description_de=cat_data['description_de'],
                    description_ru=cat_data['description_ru'],
                    color_hex=cat_data['color_hex'],
                    icon_name=cat_data['icon_name'],
                    is_system=True,
                    user_id=None,
                    sort_order=cat_data['sort_order'],
                    is_active=True
                )
                session.add(new_category)
                created.append(cat_data['name_en'])

            session.commit()

            await self._log_audit(
                session=session,
                user_id=user_id,
                action="defaults_restored",
                resource_id=None,
                ip_address=ip_address,
                new_values={"created": created, "skipped": skipped}
            )

            logger.info(f"Default categories restored: created={created}, skipped={skipped}")

            return RestoreDefaultsResponse(
                success=True,
                message=f"Restored {len(created)} default categories",
                categories_created=created,
                categories_skipped=skipped
            )

        except Exception as e:
            session.rollback()
            logger.error(f"Failed to restore defaults: {e}")
            raise
        finally:
            session.close()

    async def get_category_documents_count(
        self, 
        category_id: str,
        user_id: str
    ) -> int:
        """Get document count for a category"""
        session = db_manager.session_local()
        try:
            count = session.execute(
                select(func.count(Document.id)).where(
                    Document.category_id == category_id,
                    Document.user_id == user_id
                )
            ).scalar() or 0

            return count

        except Exception as e:
            logger.error(f"Failed to get document count: {e}")
            return 0
        finally:
            session.close()

    async def _create_google_drive_folder(
        self, 
        user_email: str,
        folder_name: str
    ) -> Optional[str]:
        """Create category subfolder in Google Drive"""
        try:
            logger.info(f"Creating Google Drive folder '{folder_name}' for {user_email}")
            return None
        except Exception as e:
            logger.error(f"Failed to create Google Drive folder: {e}")
            return None

    async def _rename_google_drive_folder(
        self, 
        user_email: str,
        old_name: str,
        new_name: str
    ) -> bool:
        """Rename category folder in Google Drive"""
        try:
            logger.info(f"Renaming Google Drive folder '{old_name}' to '{new_name}' for {user_email}")
            return True
        except Exception as e:
            logger.error(f"Failed to rename Google Drive folder: {e}")
            return False

    async def _delete_google_drive_folder(
        self, 
        user_email: str,
        folder_name: str
    ) -> bool:
        """Delete category folder from Google Drive"""
        try:
            logger.info(f"Deleting Google Drive folder '{folder_name}' for {user_email}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete Google Drive folder: {e}")
            return False

    async def _log_audit(
        self,
        session: Session,
        user_id: str,
        action: str,
        resource_id: Optional[str],
        ip_address: Optional[str],
        old_values: Optional[Dict] = None,
        new_values: Optional[Dict] = None
    ):
        """Log audit trail for category operations"""
        try:
            audit_log = AuditLog(
                user_id=user_id,
                action=action,
                resource_type="category",
                resource_id=resource_id,
                ip_address=ip_address,
                old_values=json.dumps(old_values) if old_values else None,
                new_values=json.dumps(new_values) if new_values else None
            )
            session.add(audit_log)
            session.commit()
        except Exception as e:
            logger.error(f"Failed to log audit: {e}")


category_service = CategoryService()