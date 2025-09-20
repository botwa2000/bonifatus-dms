# backend/tests/test_core_functionality.py
"""
Bonifatus DMS - Core Functionality Tests
Complete test suite for document processing, categorization, and search
"""

import pytest
import asyncio
from unittest.mock import patch, Mock, AsyncMock
from fastapi import status
from io import BytesIO

from src.database.models import User, UserTier, Document, Category, DocumentStatus
from src.services.document_service import DocumentService
from src.services.category_service import CategoryService
from src.services.search_service import SearchService


@pytest.mark.asyncio
class TestDocumentProcessing:
    """Test complete document processing functionality"""

    async def test_document_upload_and_processing(
        self, client, auth_headers, test_user, test_db_session
    ):
        """Test complete document upload and processing flow"""
        with patch("src.api.documents.AuthService") as mock_auth_class:
            mock_auth_service = Mock()
            mock_auth_class.return_value = mock_auth_service
            mock_auth_service.get_current_user.return_value = test_user

            # Create test file
            test_content = b"Test PDF content for processing"
            files = {"file": ("test.pdf", BytesIO(test_content), "application/pdf")}

            response = client.post(
                "/api/v1/documents/upload", files=files, headers=auth_headers
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert "id" in data
            assert data["filename"] == "test.pdf"
            assert data["status"] == "uploading"

    async def test_document_service_text_extraction(self, test_db_session, test_user):
        """Test document text extraction"""
        document_service = DocumentService(test_db_session)

        # Create test document
        document = Document(
            user_id=test_user.id,
            filename="test.pdf",
            original_filename="test.pdf",
            file_path="/test/path/test.pdf",
            google_drive_file_id="test_drive_id",
            title="Test Document",
            file_hash="test_hash",
            file_size_bytes=1024,
            mime_type="application/pdf",
            file_extension=".pdf",
            status=DocumentStatus.PROCESSING,
        )

        test_db_session.add(document)
        test_db_session.commit()

        # Process document
        await document_service.process_document_content(document)

        assert document.status == DocumentStatus.READY
        assert document.processed_at is not None

    async def test_keyword_extraction(self, test_db_session):
        """Test keyword extraction functionality"""
        document_service = DocumentService(test_db_session)

        test_text = "This is a financial invoice document with payment terms and contract details"
        keywords = document_service._extract_keywords(test_text)

        assert len(keywords) > 0
        assert any(
            word in ["financial", "invoice", "payment", "contract"] for word in keywords
        )

    async def test_document_list_with_filters(self, client, auth_headers, test_user):
        """Test document listing with filters"""
        with patch("src.api.documents.AuthService") as mock_auth_class, patch(
            "src.api.documents.DocumentService"
        ) as mock_doc_class:

            mock_auth_service = Mock()
            mock_auth_class.return_value = mock_auth_service
            mock_auth_service.get_current_user.return_value = test_user

            mock_doc_service = Mock()
            mock_doc_class.return_value = mock_doc_service
            mock_doc_service.list_documents = AsyncMock(
                return_value={
                    "documents": [
                        {
                            "id": 1,
                            "filename": "test1.pdf",
                            "title": "Test Document 1",
                            "status": "ready",
                            "created_at": "2024-01-01T12:00:00",
                        }
                    ],
                    "total": 1,
                    "page": 1,
                    "per_page": 20,
                    "pages": 1,
                }
            )

            response = client.get(
                "/api/v1/documents/?search=test", headers=auth_headers
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert "documents" in data
            assert "pagination" in data


@pytest.mark.asyncio
class TestCategorization:
    """Test complete categorization functionality"""

    async def test_category_initialization(self, test_db_session):
        """Test default category initialization"""
        category_service = CategoryService(test_db_session)

        result = category_service.initialize_default_categories()
        assert result is True

        # Check that categories were created
        categories = category_service.get_user_categories(
            user_id=1, include_system=True, include_user=False
        )
        assert len(categories) > 0

        # Verify essential categories exist
        category_names = [cat["name_en"] for cat in categories]
        assert "Finance" in category_names
        assert "Personal" in category_names
        assert "Business" in category_names

    async def test_category_creation_api(self, client, auth_headers, test_user):
        """Test category creation via API"""
        with patch("src.api.categories.AuthService") as mock_auth_class, patch(
            "src.api.categories.CategoryService"
        ) as mock_cat_class:

            mock_auth_service = Mock()
            mock_auth_class.return_value = mock_auth_service
            mock_auth_service.get_current_user.return_value = test_user

            mock_category = Mock()
            mock_category.id = 1
            mock_category.name_en = "Test Category"
            mock_category.name_de = "Test Kategorie"
            mock_category.color = "#FF0000"
            mock_category.icon = "📁"

            mock_cat_service = Mock()
            mock_cat_class.return_value = mock_cat_service
            mock_cat_service.initialize_default_categories = AsyncMock(
                return_value=True
            )
            mock_cat_service.create_user_category = AsyncMock(
                return_value=mock_category
            )

            category_data = {
                "name_en": "Test Category",
                "name_de": "Test Kategorie",
                "color": "#FF0000",
                "icon": "📁",
            }

            response = client.post(
                "/api/v1/categories/", json=category_data, headers=auth_headers
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["name_en"] == "Test Category"

    async def test_category_suggestion(self, test_db_session, test_user):
        """Test category suggestion functionality"""
        category_service = CategoryService(test_db_session)

        # Initialize default categories first
        category_service.initialize_default_categories()

        # Test suggestion
        test_text = "This is an invoice for office supplies with payment due date"
        suggestions = category_service.suggest_categories(test_text, test_user.id)

        assert len(suggestions) > 0
        # Should suggest Finance category for invoice-related content
        assert any(s["name_en"] == "Finance" for s in suggestions)


@pytest.mark.asyncio
class TestSearch:
    """Test complete search functionality"""

    async def test_document_search_api(self, client, auth_headers, test_user):
        """Test document search via API"""
        with patch("src.api.search.AuthService") as mock_auth_class, patch(
            "src.api.search.SearchService"
        ) as mock_search_class:

            mock_auth_service = Mock()
            mock_auth_class.return_value = mock_auth_service
            mock_auth_service.get_current_user.return_value = test_user

            mock_search_service = Mock()
            mock_search_class.return_value = mock_search_service
            mock_search_service.search_documents = AsyncMock(
                return_value={
                    "documents": [
                        {
                            "id": 1,
                            "filename": "invoice.pdf",
                            "title": "Monthly Invoice",
                            "highlighted_title": "Monthly <mark>Invoice</mark>",
                            "status": "ready",
                        }
                    ],
                    "total": 1,
                    "page": 1,
                    "per_page": 20,
                    "pages": 1,
                    "query": "invoice",
                    "search_time_ms": 50,
                    "suggestions": ["invoice terms", "payment"],
                    "filters_applied": {},
                }
            )

            search_data = {"query": "invoice", "page": 1, "per_page": 20}

            response = client.post(
                "/api/v1/search/documents", json=search_data, headers=auth_headers
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert "results" in data
            assert "pagination" in data
            assert data["query"] == "invoice"
            assert len(data["results"]) == 1

    async def test_search_service_functionality(self, test_db_session, test_user):
        """Test search service core functionality"""
        search_service = SearchService(test_db_session)

        # Test search query parsing
        search_terms = search_service._parse_search_query(
            'invoice "payment terms" contract'
        )
        assert "payment terms" in search_terms
        assert "invoice" in search_terms
        assert "contract" in search_terms

    async def test_category_search_api(self, client, auth_headers, test_user):
        """Test category search via API"""
        with patch("src.api.search.AuthService") as mock_auth_class, patch(
            "src.api.search.SearchService"
        ) as mock_search_class:

            mock_auth_service = Mock()
            mock_auth_class.return_value = mock_auth_service
            mock_auth_service.get_current_user.return_value = test_user

            mock_search_service = Mock()
            mock_search_class.return_value = mock_search_service
            mock_search_service.search_categories = AsyncMock(
                return_value={
                    "categories": [
                        {
                            "id": 1,
                            "name": "Finance",
                            "name_en": "Finance",
                            "name_de": "Finanzen",
                            "color": "#4CAF50",
                            "document_count": 5,
                        }
                    ],
                    "total": 1,
                    "query": "finance",
                    "search_time_ms": 25,
                }
            )

            response = client.get(
                "/api/v1/search/categories?q=finance", headers=auth_headers
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert "results" in data
            assert len(data["results"]) == 1
            assert data["results"][0]["name"] == "Finance"

    async def test_global_search_api(self, client, auth_headers, test_user):
        """Test global search across entities"""
        with patch("src.api.search.AuthService") as mock_auth_class, patch(
            "src.api.search.SearchService"
        ) as mock_search_class:

            mock_auth_service = Mock()
            mock_auth_class.return_value = mock_auth_service
            mock_auth_service.get_current_user.return_value = test_user

            mock_search_service = Mock()
            mock_search_class.return_value = mock_search_service
            mock_search_service.global_search = AsyncMock(
                return_value={
                    "results": {
                        "documents": {
                            "results": [{"id": 1, "title": "Test Doc"}],
                            "total": 1,
                        },
                        "categories": {
                            "results": [{"id": 1, "name": "Test Category"}],
                            "total": 1,
                        },
                    },
                    "query": "test",
                    "entities_searched": ["documents", "categories"],
                    "search_time_ms": 75,
                }
            )

            search_data = {
                "query": "test",
                "entities": ["documents", "categories"],
                "limit_per_entity": 5,
            }

            response = client.post(
                "/api/v1/search/global", json=search_data, headers=auth_headers
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert "results" in data
            assert "documents" in data["results"]
            assert "categories" in data["results"]


@pytest.mark.integration
class TestFullWorkflow:
    """Test complete DMS workflow integration"""

    async def test_complete_document_workflow(self, client, auth_headers, test_user):
        """Test complete workflow: upload -> process -> categorize -> search"""
        with patch("src.api.documents.AuthService") as mock_auth_class, patch(
            "src.api.categories.AuthService"
        ) as mock_cat_auth_class, patch(
            "src.api.search.AuthService"
        ) as mock_search_auth_class:

            # Setup auth mocks
            mock_auth_service = Mock()
            mock_auth_class.return_value = mock_auth_service
            mock_cat_auth_class.return_value = mock_auth_service
            mock_search_auth_class.return_value = mock_auth_service
            mock_auth_service.get_current_user.return_value = test_user

            # 1. Test document upload
            with patch("src.api.documents.DocumentService") as mock_doc_class:
                mock_doc_service = Mock()
                mock_doc_class.return_value = mock_doc_service
                mock_doc_service.validate_upload = AsyncMock(
                    return_value={"valid": True}
                )

                mock_document = Mock()
                mock_document.id = 1
                mock_document.filename = "test.pdf"
                mock_document.status = DocumentStatus.UPLOADING
                mock_doc_service.create_document_record = AsyncMock(
                    return_value=mock_document
                )

                test_content = b"Test PDF content"
                files = {"file": ("test.pdf", BytesIO(test_content), "application/pdf")}

                response = client.post(
                    "/api/v1/documents/upload", files=files, headers=auth_headers
                )
                assert response.status_code == status.HTTP_200_OK

            # 2. Test category listing (after upload)
            with patch("src.api.categories.CategoryService") as mock_cat_class:
                mock_cat_service = Mock()
                mock_cat_class.return_value = mock_cat_service
                mock_cat_service.initialize_default_categories = AsyncMock(
                    return_value=True
                )
                mock_cat_service.get_user_categories = AsyncMock(
                    return_value=[
                        {
                            "id": 1,
                            "name": "Finance",
                            "name_en": "Finance",
                            "name_de": "Finanzen",
                            "color": "#4CAF50",
                            "document_count": 1,
                        }
                    ]
                )

                response = client.get("/api/v1/categories/", headers=auth_headers)
                assert response.status_code == status.HTTP_200_OK
                data = response.json()
                assert len(data["categories"]) > 0

            # 3. Test search functionality
            with patch("src.api.search.SearchService") as mock_search_class:
                mock_search_service = Mock()
                mock_search_class.return_value = mock_search_service
                mock_search_service.search_documents = AsyncMock(
                    return_value={
                        "documents": [
                            {
                                "id": 1,
                                "filename": "test.pdf",
                                "title": "Test Document",
                                "status": "ready",
                            }
                        ],
                        "total": 1,
                        "page": 1,
                        "per_page": 20,
                        "pages": 1,
                        "query": "test",
                        "search_time_ms": 50,
                        "suggestions": [],
                        "filters_applied": {},
                    }
                )

                search_data = {"query": "test", "page": 1, "per_page": 20}
                response = client.post(
                    "/api/v1/search/documents", json=search_data, headers=auth_headers
                )
                assert response.status_code == status.HTTP_200_OK
                data = response.json()
                assert len(data["results"]) == 1
                assert data["results"][0]["filename"] == "test.pdf"
