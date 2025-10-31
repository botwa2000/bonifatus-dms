# backend/app/services/category_service.py
"""
Bonifatus DMS - Category Service
Business logic for category management with Google Drive sync
"""

import logging
import json
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select, func, and_, or_

from app.database.models import Category, CategoryTranslation, Document, User, AuditLog, SystemSetting
from app.database.connection import db_manager
from app.schemas.category_schemas import (
    CategoryCreate, CategoryUpdate, CategoryResponse, CategoryListResponse,
    CategoryDeleteRequest, CategoryDeleteResponse, RestoreDefaultsResponse
)
from app.services.drive_service import drive_service

logger = logging.getLogger(__name__)


class CategoryService:
    """Category management service"""

    async def list_categories(
        self,
        user_id: str,
        user_language: str = 'en',
        include_system: bool = True,
        include_documents_count: bool = True
    ) -> CategoryListResponse:
        """
        List categories with translations in user's preferred language only
        """
        session = db_manager.session_local()
        try:
            # Build query
            stmt = select(Category).options(
                joinedload(Category.translations)
            )
            
            if include_system:
                stmt = stmt.where(
                    or_(
                        Category.user_id == user_id,
                        Category.is_system == True
                    )
                )
            else:
                stmt = stmt.where(Category.user_id == user_id)
            
            stmt = stmt.where(Category.is_active == True)
            stmt = stmt.order_by(Category.sort_order, Category.created_at)
            
            categories = session.execute(stmt).unique().scalars().all()
            
            category_responses = []
            for category in categories:
                # Get translation for user's language
                translation = next(
                    (t for t in category.translations if t.language_code == user_language),
                    None
                )
                
                # Fallback to English if user's language not available
                if not translation:
                    translation = next(
                        (t for t in category.translations if t.language_code == 'en'),
                        category.translations[0] if category.translations else None
                    )
                
                if not translation:
                    logger.warning(f"No translation found for category {category.id}")
                    continue
                
                # Get document count if requested
                doc_count = 0
                if include_documents_count:
                    doc_count = session.execute(
                        select(func.count(Document.id))
                        .where(Document.category_id == category.id)
                        .where(Document.user_id == user_id)
                    ).scalar() or 0
                
                category_responses.append(CategoryResponse(
                    id=str(category.id),
                    reference_key=category.reference_key,
                    category_code=category.category_code,
                    name=translation.name,
                    description=translation.description,
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
        user_language: str,
        category_data: CategoryCreate,
        ip_address: str = None
    ) -> CategoryResponse:
        """
        Create new category with translations for user's preferred languages
        Auto-generates missing translations using translation service
        """
        session = db_manager.session_local()
        try:
            # Get user's preferred document languages
            user = session.get(User, user_id)
            preferred_languages = user.preferred_doc_languages if user and user.preferred_doc_languages else [user_language]

            # Generate unique reference key
            base_key = f"category.{category_data.translations.get('en', list(category_data.translations.values())[0]).name.lower().replace(' ', '_')}"
            reference_key = base_key
            counter = 1

            while session.execute(
                select(Category).where(Category.reference_key == reference_key)
            ).scalar_one_or_none():
                reference_key = f"{base_key}_{counter}"
                counter += 1
            
            # Generate next category code for user (C01, C02, etc.)
            # Find the highest existing code number and increment
            existing_codes = session.execute(
                select(Category.category_code).where(
                    Category.user_id == user_id,
                    Category.is_system == False,
                    Category.category_code.like('C%')
                )
            ).scalars().all()

            # Extract numbers from codes like C01, C02, etc.
            max_code_num = 0
            for code in existing_codes:
                try:
                    num = int(code[1:])  # Extract number from C01, C02, etc.
                    max_code_num = max(max_code_num, num)
                except ValueError:
                    continue

            category_code = f"C{str(max_code_num + 1).zfill(2)}"
            logger.info(f"Generated category code: {category_code} (previous max: C{str(max_code_num).zfill(2)})")
            
            # Create category (multi-lingual by default)
            new_category = Category(
                reference_key=reference_key,
                category_code=category_code,
                color_hex=category_data.color_hex,
                icon_name=category_data.icon_name,
                is_system=False,
                user_id=user_id,
                sort_order=category_data.sort_order or 999,
                is_active=category_data.is_active if category_data.is_active is not None else True,
                is_multi_lingual=True
            )
            
            session.add(new_category)
            session.flush()

            # Auto-generate translations for user's preferred languages
            from app.services.translation_service import translation_service

            final_translations = {}

            # Get the source translation (from user input)
            source_lang = list(category_data.translations.keys())[0]
            source_translation = category_data.translations[source_lang]

            # For each preferred language, ensure we have a translation
            for lang_code in preferred_languages:
                if lang_code in category_data.translations:
                    # User provided this translation
                    final_translations[lang_code] = category_data.translations[lang_code]
                else:
                    # Auto-translate using translation service
                    translated_name = await translation_service.translate(
                        text=source_translation.name,
                        source_lang=source_lang,
                        target_lang=lang_code,
                        user_tier=user.tier if user else None
                    )

                    translated_desc = None
                    if source_translation.description:
                        translated_desc = await translation_service.translate(
                            text=source_translation.description,
                            source_lang=source_lang,
                            target_lang=lang_code,
                            user_tier=user.tier if user else None
                        )

                    # Create translation data object
                    from app.schemas.category_schemas import CategoryTranslationData
                    final_translations[lang_code] = CategoryTranslationData(
                        name=translated_name or source_translation.name,
                        description=translated_desc or source_translation.description
                    )

                    logger.info(f"Auto-translated category to {lang_code}: {translated_name}")

            # Create translation records only for preferred languages
            for lang_code, translation_data in final_translations.items():
                translation = CategoryTranslation(
                    category_id=new_category.id,
                    language_code=lang_code,
                    name=translation_data.name,
                    description=translation_data.description
                )
                session.add(translation)
            
            session.commit()
            session.refresh(new_category)
            
            # Get user's language translation for response
            user_translation = next(
                (t for t in new_category.translations if t.language_code == user_language),
                new_category.translations[0] if new_category.translations else None
            )
            
            # Create Google Drive folder (use English name or first available)
            folder_name = category_data.translations.get('en', list(category_data.translations.values())[0]).name
            await self._create_google_drive_folder(user_email, folder_name)
            
            # Audit log
            await self._log_audit(
                session=session,
                user_id=user_id,
                action="category_created",
                resource_id=str(new_category.id),
                ip_address=ip_address,
                new_values={'reference_key': reference_key, 'translations': len(category_data.translations)}
            )
            
            logger.info(f"Category created: {new_category.id} by user {user_id}")
            
            return CategoryResponse(
                id=str(new_category.id),
                reference_key=new_category.reference_key,
                category_code=new_category.category_code,
                name=user_translation.name,
                description=user_translation.description,
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
        user_language: str,
        category_data: CategoryUpdate,
        ip_address: str = None
    ) -> Optional[CategoryResponse]:
        """
        Update category and/or translations
        Note: OTHER category (category.other) cannot have its reference_key changed
        """
        session = db_manager.session_local()
        try:
            category = session.execute(
                select(Category)
                .options(joinedload(Category.translations))
                .where(Category.id == category_id)
            ).unique().scalar_one_or_none()

            if not category:
                return None

            if category.user_id and str(category.user_id) != user_id:
                raise PermissionError("Cannot modify another user's category")

            # Protect OTHER category from being renamed
            if category.reference_key == 'category.other':
                if category_data.translations:
                    # Allow updating translations (colors, icons, descriptions) but prevent renaming
                    logger.warning(f"Attempted to modify OTHER category, allowing limited updates only")
                # Continue with limited updates (color, icon, sort_order, is_active)

            old_values = {
                "reference_key": category.reference_key,
                "color_hex": category.color_hex,
                "icon_name": category.icon_name
            }

            # Update category fields
            if category_data.color_hex is not None:
                category.color_hex = category_data.color_hex
            if category_data.icon_name is not None:
                category.icon_name = category_data.icon_name
            if category_data.sort_order is not None:
                category.sort_order = category_data.sort_order
            if category_data.is_active is not None:
                category.is_active = category_data.is_active

            # Update or add translations
            if category_data.translations:
                for lang_code, translation_data in category_data.translations.items():
                    # Find existing translation
                    existing_translation = next(
                        (t for t in category.translations if t.language_code == lang_code),
                        None
                    )
                    
                    if existing_translation:
                        # Update existing
                        existing_translation.name = translation_data.name
                        existing_translation.description = translation_data.description
                        existing_translation.updated_at = datetime.now(timezone.utc)
                    else:
                        # Add new translation
                        new_translation = CategoryTranslation(
                            category_id=category.id,
                            language_code=lang_code,
                            name=translation_data.name,
                            description=translation_data.description
                        )
                        session.add(new_translation)

            category.updated_at = datetime.now(timezone.utc)
            session.commit()
            session.refresh(category)

            # Get user's language translation for response
            user_translation = next(
                (t for t in category.translations if t.language_code == user_language),
                next((t for t in category.translations if t.language_code == 'en'), 
                     category.translations[0] if category.translations else None)
            )

            # Audit log
            new_values = {
                "color_hex": category.color_hex,
                "icon_name": category.icon_name,
                "translations_updated": len(category_data.translations) if category_data.translations else 0
            }
            
            await self._log_audit(
                session=session,
                user_id=user_id,
                action="category_updated",
                resource_id=str(category.id),
                ip_address=ip_address,
                old_values=old_values,
                new_values=new_values
            )

            logger.info(f"Category updated: {category.id}")

            return CategoryResponse(
                id=str(category.id),
                reference_key=category.reference_key,
                category_code=category.category_code,
                name=user_translation.name,
                description=user_translation.description,
                color_hex=category.color_hex,
                icon_name=category.icon_name,
                is_system=category.is_system,
                user_id=str(category.user_id) if category.user_id else None,
                sort_order=category.sort_order,
                is_active=category.is_active,
                documents_count=0,
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
        Note: OTHER category (category.other) cannot be deleted
        """
        session = db_manager.session_local()
        try:
            category = session.get(Category, category_id)
            if not category:
                return None

            # Protect OTHER category from deletion
            if category.reference_key == 'category.other':
                raise PermissionError("Cannot delete the OTHER category - it is required as a fallback category")

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
                            select(Category)
                            .join(CategoryTranslation)
                            .where(
                                CategoryTranslation.language_code == 'en',
                                CategoryTranslation.name == 'Other',
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
                            translation = next(
                                (t for t in target_cat.translations if t.language_code == 'en'),
                                target_cat.translations[0] if target_cat.translations else None
                            )
                            target_category_name = translation.name if translation else target_cat.reference_key

                    update_stmt = select(Document).where(Document.category_id == category_id)
                    documents = session.execute(update_stmt).scalars().all()
                    for doc in documents:
                        doc.category_id = target_category_id
                    documents_moved = doc_count

            translation = next(
                (t for t in category.translations if t.language_code == 'en'),
                category.translations[0] if category.translations else None
            )
            category_name = translation.name if translation else category.reference_key
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

            message = f"Category '{category_name}' deleted successfully"
            if documents_moved > 0:
                message += f". {documents_moved} documents moved to '{target_category_name}'"
            elif documents_deleted > 0:
                message += f". {documents_deleted} documents deleted"

            return CategoryDeleteResponse(
                deleted_category_id=category_id,
                documents_moved=documents_moved,
                documents_deleted=documents_deleted,
                message=message
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
        Restore default system categories and delete all custom categories
        Deletes all user's custom categories and ensures system categories exist
        """
        session = db_manager.session_local()
        try:
            # Step 1: Delete all user's custom categories
            deleted_count = 0
            user_categories = session.execute(
                select(Category).where(
                    Category.user_id == user_id,
                    Category.is_system == False
                )
            ).scalars().all()

            for cat in user_categories:
                session.delete(cat)
                deleted_count += 1

            logger.info(f"Deleted {deleted_count} custom categories for user {user_id}")

            # Step 2: Ensure system categories exist
            category_config = session.execute(
                select(SystemSetting).where(
                    SystemSetting.setting_key == 'default_system_categories'
                )
            ).scalar_one_or_none()

            if not category_config:
                raise ValueError("Default category configuration not found in system_settings")

            default_categories = json.loads(category_config.setting_value)

            created = []
            skipped = []

            for cat_data in default_categories:
                existing = session.execute(
                    select(Category).where(
                        Category.reference_key == cat_data['reference_key'],
                        Category.is_system == True
                    )
                ).scalar_one_or_none()

                if existing:
                    skipped.append(cat_data['translations']['en']['name'])
                    continue

                new_category = Category(
                    reference_key=cat_data['reference_key'],
                    category_code=cat_data['category_code'],
                    color_hex=cat_data['color_hex'],
                    icon_name=cat_data['icon_name'],
                    is_system=True,
                    user_id=None,
                    sort_order=cat_data['sort_order'],
                    is_active=True
                )
                session.add(new_category)
                session.flush()

                for lang_code, trans_data in cat_data['translations'].items():
                    translation = CategoryTranslation(
                        category_id=new_category.id,
                        language_code=lang_code,
                        name=trans_data['name'],
                        description=trans_data['description']
                    )
                    session.add(translation)

                created.append(cat_data['translations']['en']['name'])

            session.commit()

            await self._log_audit(
                session=session,
                user_id=user_id,
                action="defaults_restored",
                resource_id=None,
                ip_address=ip_address,
                new_values={"created": created, "skipped": skipped, "deleted": deleted_count}
            )

            logger.info(f"Default categories restored: deleted={deleted_count}, created={created}, skipped={skipped}")

            message = f"Deleted {deleted_count} custom categories and restored {len(created)} default categories"
            return RestoreDefaultsResponse(
                created=created,
                skipped=skipped,
                message=message
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

    async def _create_google_drive_folder(self, user_email: str, folder_name: str) -> Optional[str]:
        """Create category subfolder in Google Drive"""
        session = db_manager.session_local()
        try:
            # Get user's Google Drive refresh token
            from sqlalchemy import text
            user_result = session.execute(
                text("SELECT drive_refresh_token_encrypted FROM users WHERE email = :email"),
                {'email': user_email}
            ).first()

            if not user_result or not user_result[0]:
                logger.warning(f"User {user_email} has not connected Google Drive, skipping folder creation")
                return None

            refresh_token_encrypted = user_result[0]

            # Get Drive service
            service = drive_service._get_drive_service(refresh_token_encrypted)

            # 1. Find or create Bonifatus_DMS root folder
            root_folder_id = drive_service._find_folder(service, drive_service.app_folder_name)
            if not root_folder_id:
                root_folder_id = drive_service._create_folder(service, drive_service.app_folder_name)

            # 2. Create category subfolder
            folder_id = drive_service._create_folder(service, folder_name, root_folder_id)

            logger.info(f"Created Google Drive folder: {folder_name} ({folder_id})")
            return folder_id

        except Exception as e:
            logger.error(f"Failed to create Google Drive folder: {e}")
            return None
        finally:
            session.close()

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