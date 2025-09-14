# backend/tests/test_documents.py
"""
Bonifatus DMS - Document Tests
Comprehensive tests for document upload, processing, and management
"""

import pytest
import io
from unittest.mock import patch, Mock, AsyncMock
from fastapi import status, UploadFile

from src.database.models import Document, DocumentStatus, UserTier
from src.services.document_service import DocumentService


@pytest.mark.integration
class TestDocumentUpload:
    """Test document upload functionality"""
    
    def test_upload_document_success(self, client, auth_headers, test_user, test_category, mock_google_drive):
        """Test successful document upload"""
        # Mock file content
        file_content = b"Test PDF content for upload"
        
        with patch('src.api.documents.AuthService') as mock_auth_class, \
             patch('src.api.documents.DocumentService') as mock_doc_class, \
             patch('src.api.documents.GoogleDriveClient') as mock_drive_class:
            
            # Setup mocks
            mock_auth_service = Mock()
            mock_auth_class.return_value = mock_auth_service
            mock_auth_service.get_current_user.return_value = test_user
            
            mock_doc_service = Mock()
            mock_doc_class.return_value = mock_doc_service
            mock_doc_service.validate_upload.return_value = {"valid": True}
            
            # Mock document creation
            test_document = Document(
                id=1,
                user_id=test_user.id,
                category_id=test_category.id,
                filename="test_document_20240101_120000.pdf",
                original_filename="test_document.pdf",
                file_path="/Test Category/test_document.pdf",
                google_drive_file_id="test_file_id_123",
                file_size_bytes=len(file_content),
                mime_type="application/pdf",
                file_extension=".pdf",
                status=DocumentStatus.UPLOADING
            )
            mock_doc_service.create_document_record.return_value = test_document
            
            mock_drive_class.return_value = mock_google_drive
            
            # Create file upload
            files = {
                "file": ("test_document.pdf", io.BytesIO(file_content), "application/pdf")
            }
            data = {
                "category_id": test_category.id,
                "title": "Test Document",
                "description": "Test document description"
            }
            
            response = client.post("/api/v1/documents/upload", files=files, data=data, headers=auth_headers)
            
            assert response.status_code == status.HTTP_200_OK
            response_data = response.json()
            assert response_data["document_id"] == 1
            assert response_data["filename"] == "test_document_20240101_120000.pdf"
            assert response_data["status"] == "uploading"
    
    def test_upload_document_file_too_large(self, client, auth_headers, test_user):
        """Test upload with file exceeding size limit"""
        # Create large mock file
        large_content = b"x" * (51 * 1024 * 1024)  # 51MB
        
        with patch('src.api.documents.AuthService') as mock_auth_class, \
             patch('src.api.documents.DocumentService') as mock_doc_class:
            
            mock_auth_service = Mock()
            mock_auth_class.return_value = mock_auth_service
            mock_auth_service.get_current_user.return_value = test_user
            
            mock_doc_service = Mock()
            mock_doc_class.return_value = mock_doc_service
            mock_doc_service.validate_upload.return_value = {
                "valid": False,
                "error": "File size exceeds 50MB limit"
            }
            
            files = {
                "file": ("large_file.pdf", io.BytesIO(large_content), "application/pdf")
            }
            
            response = client.post("/api/v1/documents/upload", files=files, headers=auth_headers)
            
            assert response.status_code == status.HTTP_400_BAD_REQUEST
            assert "exceeds 50MB limit" in response.json()["detail"]
    
    def test_upload_document_unsupported_type(self, client, auth_headers, test_user):
        """Test upload with unsupported file type"""
        file_content = b"Unsupported content"
        
        with patch('src.api.documents.AuthService') as mock_auth_class, \
             patch('src.api.documents.DocumentService') as mock_doc_class:
            
            mock_auth_service = Mock()
            mock_auth_class.return_value = mock_auth_service
            mock_auth_service.get_current_user.return_value = test_user
            
            mock_doc_service = Mock()
            mock_doc_class.return_value = mock_doc_service
            mock_doc_service.validate_upload.return_value = {
                "valid": False,
                "error": "File type .exe not supported"
            }
            
            files = {
                "file": ("malware.exe", io.BytesIO(file_content), "application/octet-stream")
            }
            
            response = client.post("/api/v1/documents/upload", files=files, headers=auth_headers)
            
            assert response.status_code == status.HTTP_400_BAD_REQUEST
            assert "not supported" in response.json()["detail"]
    
    def test_upload_document_limit_reached(self, client, auth_headers, test_user):
        """Test upload when user has reached document limit"""
        # Set user to document limit
        test_user.document_count = 100  # Free tier limit
        test_user.tier = UserTier.FREE
        
        with patch('src.api.documents.AuthService') as mock_auth_class, \
             patch('src.api.documents.DocumentService') as mock_doc_class:
            
            mock_auth_service = Mock()
            mock_auth_class.return_value = mock_auth_service
            mock_auth_service.get_current_user.return_value = test_user
            
            mock_doc_service = Mock()
            mock_doc_class.return_value = mock_doc_service
            mock_doc_service.validate_upload.return_value = {
                "valid": False,
                "error": "Document limit reached (100 documents)"
            }
            
            files = {
                "file": ("test.pdf", io.BytesIO(b"content"), "application/pdf")
            }
            
            response = client.post("/api/v1/documents/upload", files=files, headers=auth_headers)
            
            assert response.status_code == status.HTTP_400_BAD_REQUEST
            assert "Document limit reached" in response.json()["detail"]


@pytest.mark.integration
class TestDocumentManagement:
    """Test document management operations"""
    
    def test_list_documents_success(self, client, auth_headers, test_user):
        """Test listing user documents"""
        with patch('src.api.documents.AuthService') as mock_auth_class, \
             patch('src.api.documents.DocumentService') as mock_doc_class:
            
            mock_auth_service = Mock()
            mock_auth_class.return_value = mock_auth_service
            mock_auth_service.get_current_user.return_value = test_user
            
            mock_doc_service = Mock()
            mock_doc_class.return_value = mock_doc_service
            mock_doc_service.list_documents.return_value = {
                "documents": [
                    {
                        "id": 1,
                        "filename": "test1.pdf",
                        "title": "Test Document 1",
                        "status": "ready",
                        "created_at": "2024-01-01T12:00:00"
                    },
                    {
                        "id": 2,
                        "filename": "test2.pdf", 
                        "title": "Test Document 2",
                        "status": "ready",
                        "created_at": "2024-01-02T12:00:00"
                    }
                ],
                "total": 2
            }
            
            response = client.get("/api/v1/documents/", headers=auth_headers)
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert len(data["documents"]) == 2
            assert data["pagination"]["total"] == 2
            assert data["documents"][0]["filename"] == "test1.pdf"
    
    def test_get_document_success(self, client, auth_headers, test_user, test_document):
        """Test getting specific document"""
        with patch('src.api.documents.AuthService') as mock_auth_class:
            mock_auth_service = Mock()
            mock_auth_class.return_value = mock_auth_service
            mock_auth_service.get_current_user.return_value = test_user
            
            # Mock database query
            with patch('src.api.documents.db.query') as mock_query:
                mock_query.return_value.filter.return_value.first.return_value = test_document
                
                response = client.get(f"/api/v1/documents/{test_document.id}", headers=auth_headers)
                
                assert response.status_code == status.HTTP_200_OK
                data = response.json()
                assert data["id"] == test_document.id
                assert data["filename"] == test_document.filename
    
    def test_get_document_not_found(self, client, auth_headers, test_user):
        """Test getting non-existent document"""
        with patch('src.api.documents.AuthService') as mock_auth_class:
            mock_auth_service = Mock()
            mock_auth_class.return_value = mock_auth_service
            mock_auth_service.get_current_user.return_value = test_user
            
            with patch('src.api.documents.db.query') as mock_query:
                mock_query.return_value.filter.return_value.first.return_value = None
                
                response = client.get("/api/v1/documents/999", headers=auth_headers)
                
                assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_update_document_success(self, client, auth_headers, test_user, test_document):
        """Test updating document metadata"""
        update_data = {
            "title": "Updated Title",
            "description": "Updated description",
            "is_favorite": True
        }
        
        with patch('src.api.documents.AuthService') as mock_auth_class:
            mock_auth_service = Mock()
            mock_auth_class.return_value = mock_auth_service
            mock_auth_service.get_current_user.return_value = test_user
            
            with patch('src.api.documents.db.query') as mock_query, \
                 patch('src.api.documents.db.commit') as mock_commit:
                mock_query.return_value.filter.return_value.first.return_value = test_document
                
                response = client.put(f"/api/v1/documents/{test_document.id}", 
                                    json=update_data, headers=auth_headers)
                
                assert response.status_code == status.HTTP_200_OK
                data = response.json()
                assert data["success"] is True
    
    def test_delete_document_success(self, client, auth_headers, test_user, test_document, mock_google_drive):
        """Test deleting document"""
        with patch('src.api.documents.AuthService') as mock_auth_class, \
             patch('src.api.documents.GoogleDriveClient') as mock_drive_class:
            
            mock_auth_service = Mock()
            mock_auth_class.return_value = mock_auth_service  
            mock_auth_service.get_current_user.return_value = test_user
            
            mock_drive_class.return_value = mock_google_drive
            
            with patch('src.api.documents.db.query') as mock_query, \
                 patch('src.api.documents.db.delete') as mock_delete, \
                 patch('src.api.documents.db.commit') as mock_commit:
                mock_query.return_value.filter.return_value.first.return_value = test_document
                
                response = client.delete(f"/api/v1/documents/{test_document.id}?permanent=true", 
                                       headers=auth_headers)
                
                assert response.status_code == status.HTTP_200_OK
                data = response.json()
                assert data["success"] is True
                assert data["deleted_from_drive"] is True


@pytest.mark.unit
class TestDocumentService:
    """Test DocumentService business logic"""
    
    @pytest.mark.asyncio
    async def test_validate_upload_success(self, test_db_session, test_user):
        """Test successful upload validation"""
        document_service = DocumentService(test_db_session)
        
        # Mock file
        mock_file = Mock()
        mock_file.filename = "test.pdf"
        mock_file.size = 1024 * 1024  # 1MB
        
        result = await document_service.validate_upload(test_user, mock_file, max_size_mb=50)
        
        assert result["valid"] is True
    
    @pytest.mark.asyncio
    async def test_validate_upload_file_too_large(self, test_db_session, test_user):
        """Test upload validation with oversized file"""
        document_service = DocumentService(test_db_session)
        
        mock_file = Mock()
        mock_file.filename = "large.pdf"
        mock_file.size = 60 * 1024 * 1024  # 60MB
        
        result = await document_service.validate_upload(test_user, mock_file, max_size_mb=50)
        
        assert result["valid"] is False
        assert "exceeds 50MB limit" in result["error"]
    
    @pytest.mark.asyncio
    async def test_create_document_record(self, test_db_session, test_user, test_category):
        """Test creating document record"""
        document_service = DocumentService(test_db_session)
        
        mock_file = Mock()
        mock_file.filename = "test.pdf"
        mock_file.content_type = "application/pdf"
        mock_file.size = 1024
        mock_file.file = io.BytesIO(b"test content")
        
        document = await document_service.create_document_record(
            user_id=test_user.id,
            file=mock_file,
            category_id=test_category.id,
            title="Test Document"
        )
        
        assert document is not None
        assert document.user_id == test_user.id
        assert document.category_id == test_category.id
        assert document.title == "Test Document"
        assert document.status == DocumentStatus.UPLOADING
        assert document.original_filename == "test.pdf"
    
    @pytest.mark.asyncio
    async def test_extract_keywords(self, test_db_session):
        """Test keyword extraction from text"""
        document_service = DocumentService(test_db_session)
        
        sample_text = """
        This is a financial document containing information about invoices,
        payments, and accounting records. The document discusses revenue,
        expenses, and profit margins for the fiscal year.
        """
        
        keywords = await document_service._extract_keywords(sample_text, "en")
        
        assert isinstance(keywords, list)
        assert len(keywords) > 0
        assert "financial" in keywords
        assert "document" in keywords
        assert "invoice" in keywords or "invoices" in keywords
    
    def test_detect_language_english(self, test_db_session):
        """Test language detection for English text"""
        document_service = DocumentService(test_db_session)
        
        english_text = "This is an English document with typical English words and phrases."
        
        language = document_service._detect_language(english_text)
        
        assert language == "en"
    
    def test_detect_language_german(self, test_db_session):
        """Test language detection for German text"""
        document_service = DocumentService(test_db_session)
        
        german_text = "Dies ist ein deutsches Dokument mit typischen deutschen Wörtern und Phrasen."
        
        language = document_service._detect_language(german_text)
        
        assert language == "de"


# Fixtures for document tests
@pytest.fixture
def test_document(test_db_session, test_user, test_category):
    """Create a test document"""
    document = Document(
        user_id=test_user.id,
        category_id=test_category.id,
        filename="test_document.pdf",
        original_filename="Original Test Document.pdf",
        file_path="/Test Category/test_document.pdf",
        google_drive_file_id="test_file_id_123",
        file_size_bytes=1024000,
        mime_type="application/pdf",
        file_extension=".pdf",
        status=DocumentStatus.READY,
        title="Test Document",
        description="Test document description"
    )
    
    test_db_session.add(document)
    test_db_session.commit()
    test_db_session.refresh(document)
    
    return document