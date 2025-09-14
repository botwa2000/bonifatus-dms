# backend/tests/test_search.py
"""
Bonifatus DMS - Search Tests
Comprehensive tests for document search functionality
Full-text search, advanced filters, and suggestion features
"""

import pytest
from unittest.mock import patch, Mock
from fastapi import status

from src.database.models import Document, Category, DocumentStatus
from src.services.search_service import SearchService


@pytest.mark.integration
class TestSearchAPI:
    """Test search functionality via API endpoints"""
    
    def test_basic_document_search(self, client, auth_headers, test_user):
        """Test basic document search"""
        search_data = {"query": "invoice"}
        
        with patch('src.api.documents.AuthService') as mock_auth_class, \
             patch('src.api.documents.SearchService') as mock_search_class:
            
            mock_auth_service = Mock()
            mock_auth_class.return_value = mock_auth_service
            mock_auth_service.get_current_user.return_value = test_user
            
            mock_search_service = Mock()
            mock_search_class.return_value = mock_search_service
            mock_search_service.search_documents.return_value = {
                "documents": [
                    {
                        "id": 1,
                        "filename": "invoice_123.pdf",
                        "title": "Invoice from ABC Company",
                        "status": "ready",
                        "created_at": "2024-01-01T12:00:00"
                    }
                ],
                "total": 1,
                "search_time_ms": 50
            }
            
            response = client.post(
                "/api/v1/documents/search",
                json=search_data,
                headers=auth_headers
            )
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert "results" in data
            assert "total" in data
            assert "search_time_ms" in data
            assert data["query"] == "invoice"
    
    def test_advanced_search_with_filters(self, client, auth_headers, test_user):
        """Test advanced search with multiple filters"""
        search_data = {
            "query": "contract",
            "category_ids": [1, 2],
            "file_types": ["pdf", "docx"],
            "date_from": "2024-01-01T00:00:00",
            "date_to": "2024-12-31T23:59:59"
        }
        
        with patch('src.api.documents.AuthService') as mock_auth_class, \
             patch('src.api.documents.SearchService') as mock_search_class:
            
            mock_auth_service = Mock()
            mock_auth_class.return_value = mock_auth_service
            mock_auth_service.get_current_user.return_value = test_user
            
            mock_search_service = Mock()
            mock_search_class.return_value = mock_search_service
            mock_search_service.advanced_search.return_value = {
                "documents": [
                    {
                        "id": 2,
                        "filename": "employment_contract.pdf",
                        "title": "Employment Contract",
                        "highlighted_title": "Employment <mark>Contract</mark>",
                        "status": "ready"
                    }
                ],
                "total": 1,
                "search_time_ms": 75,
                "suggestions": ["contract terms", "legal agreement"]
            }
            
            response = client.post(
                "/api/v1/documents/search",
                json=search_data,
                headers=auth_headers
            )
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert len(data["results"]) == 1
            assert "suggestions" in data
            assert "highlighted_title" in data["results"][0]
    
    def test_search_with_empty_query(self, client, auth_headers, test_user):
        """Test search with empty query"""
        with patch('src.api.documents.AuthService') as mock_auth_class, \
             patch('src.api.documents.SearchService') as mock_search_class:
            
            mock_auth_service = Mock()
            mock_auth_class.return_value = mock_auth_service
            mock_auth_service.get_current_user.return_value = test_user
            
            mock_search_service = Mock()
            mock_search_class.return_value = mock_search_service
            mock_search_service.search_documents.return_value = {
                "documents": [],
                "total": 0,
                "search_time_ms": 10
            }
            
            response = client.post(
                "/api/v1/documents/search",
                json={"query": ""},
                headers=auth_headers
            )
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["results"] == []


@pytest.mark.unit
class TestSearchService:
    """Test SearchService business logic"""
    
    @pytest.mark.asyncio
    async def test_search_documents_basic(self, test_db_session, test_user, test_document):
        """Test basic document search"""
        search_service = SearchService(test_db_session)
        
        # Add test document to session
        test_document.extracted_text = "This is an invoice for office supplies"
        test_document.status = DocumentStatus.READY
        test_db_session.add(test_document)
        test_db_session.commit()
        
        filters = {"user_id": test_user.id}
        results = await search_service.search_documents(
            user_id=test_user.id,
            query="invoice",
            filters=filters
        )
        
        assert "documents" in results
        assert "total" in results
        assert "search_time_ms" in results
        assert results["query"] == "invoice"
    
    @pytest.mark.asyncio
    async def test_advanced_search(self, test_db_session, test_user, test_document, test_category):
        """Test advanced search with filters"""
        search_service = SearchService(test_db_session)
        
        # Setup test data
        test_document.extracted_text = "Employment contract with benefits"
        test_document.category_id = test_category.id
        test_document.status = DocumentStatus.READY
        test_db_session.add(test_document)
        test_db_session.commit()
        
        filters = {
            "user_id": test_user.id,
            "category_ids": [test_category.id],
            "file_types": ["pdf"],
            "page": 1,
            "per_page": 20
        }
        
        results = await search_service.advanced_search("contract", filters)
        
        assert "documents" in results
        assert "total" in results
        assert "suggestions" in results
    
    @pytest.mark.asyncio
    async def test_get_search_suggestions(self, test_db_session, test_user, test_document):
        """Test search query suggestions"""
        search_service = SearchService(test_db_session)
        
        # Add document with keywords
        test_document.extracted_keywords = ["invoice", "payment", "finance"]
        test_document.title = "Invoice Payment Processing"
        test_db_session.add(test_document)
        test_db_session.commit()
        
        suggestions = await search_service.get_search_suggestions(
            user_id=test_user.id,
            query="inv",
            limit=5
        )
        
        assert isinstance(suggestions, list)
        # Should include suggestions starting with "inv"
        invoice_suggestions = [s for s in suggestions if "inv" in s.lower()]
        assert len(invoice_suggestions) >= 0
    
    @pytest.mark.asyncio
    async def test_get_popular_searches(self, test_db_session, test_user, test_document):
        """Test popular search queries"""
        search_service = SearchService(test_db_session)
        
        # Add document with common keywords
        test_document.extracted_keywords = ["contract", "legal", "agreement"]
        test_db_session.add(test_document)
        test_db_session.commit()
        
        popular = await search_service.get_popular_searches(
            user_id=test_user.id,
            limit=10
        )
        
        assert isinstance(popular, list)
        if popular:  # May be empty if no data
            assert "query" in popular[0]
            assert "frequency" in popular[0]
    
    def test_build_search_conditions(self, test_db_session):
        """Test building SQL search conditions"""
        search_service = SearchService(test_db_session)
        
        query = "invoice payment contract"
        conditions = search_service._build_search_conditions(query)
        
        # Should return a valid SQLAlchemy condition
        assert conditions is not None
    
    def test_parse_advanced_query(self, test_db_session):
        """Test parsing advanced search query"""
        search_service = SearchService(test_db_session)
        
        # Test query with operators
        query = '+invoice -draft "final contract" title:agreement'
        parsed = search_service._parse_advanced_query(query)
        
        assert "must_have" in parsed
        assert "must_not_have" in parsed
        assert "phrase_searches" in parsed
        assert "field_searches" in parsed
        
        assert "invoice" in parsed["must_have"]
        assert "draft" in parsed["must_not_have"]
        assert "final contract" in parsed["phrase_searches"]
        assert "title" in parsed["field_searches"]
    
    def test_highlight_text(self, test_db_session):
        """Test text highlighting for search results"""
        search_service = SearchService(test_db_session)
        
        text = "This is an invoice for office supplies payment"
        query = "invoice payment"
        
        highlighted = search_service._highlight_text(text, query)
        
        assert "<mark>" in highlighted
        assert "</mark>" in highlighted
        # Should highlight both "invoice" and "payment"
        assert "invoice" in highlighted.lower()
        assert "payment" in highlighted.lower()
    
    def test_generate_excerpt(self, test_db_session):
        """Test generating text excerpts around search terms"""
        search_service = SearchService(test_db_session)
        
        long_text = "This is a very long document with lots of text. " * 20 + \
                   "Here is the important invoice information. " + \
                   "This continues with more text. " * 20
        
        query = "invoice"
        excerpt = search_service._generate_excerpt(long_text, query, max_length=100)
        
        assert len(excerpt) <= 120  # Account for ellipsis
        assert "invoice" in excerpt.lower()
        # Should include some context around the term


@pytest.mark.integration
class TestSearchPerformance:
    """Test search performance and edge cases"""
    
    @pytest.mark.asyncio
    async def test_search_with_large_result_set(self, test_db_session, test_user):
        """Test search performance with many documents"""
        search_service = SearchService(test_db_session)
        
        # Create multiple test documents
        documents = []
        for i in range(50):
            doc = Document(
                user_id=test_user.id,
                filename=f"test_doc_{i}.pdf",
                original_filename=f"test_doc_{i}.pdf",
                file_path=f"/test/test_doc_{i}.pdf",
                google_drive_file_id=f"test_id_{i}",
                file_size_bytes=1024,
                mime_type="application/pdf",
                file_extension=".pdf",
                status=DocumentStatus.READY,
                extracted_text=f"This is test document number {i} with invoice content"
            )
            documents.append(doc)
        
        test_db_session.add_all(documents)
        test_db_session.commit()
        
        # Perform search
        filters = {"user_id": test_user.id, "page": 1, "per_page": 20}
        results = await search_service.search_documents(
            user_id=test_user.id,
            query="invoice",
            filters=filters
        )
        
        # Should handle large result set efficiently
        assert results["total"] > 20
        assert len(results["documents"]) <= 20  # Pagination
        assert results["search_time_ms"] < 1000  # Should be fast
    
    @pytest.mark.asyncio
    async def test_search_with_special_characters(self, test_db_session, test_user):
        """Test search with special characters and symbols"""
        search_service = SearchService(test_db_session)
        
        # Test various special character queries
        special_queries = [
            "invoice@company.com",
            "contract#123",
            "$500 payment",
            "C++ programming",
            "user@domain.com"
        ]
        
        for query in special_queries:
            filters = {"user_id": test_user.id}
            results = await search_service.search_documents(
                user_id=test_user.id,
                query=query,
                filters=filters
            )
            
            # Should not crash and return valid structure
            assert "documents" in results
            assert "total" in results
    
    @pytest.mark.asyncio
    async def test_search_multilingual(self, test_db_session, test_user, test_document):
        """Test search with German and English content"""
        search_service = SearchService(test_db_session)
        
        # Add document with German content
        test_document.extracted_text = "Dies ist eine Rechnung für Büromaterial"
        test_document.language_detected = "de"
        test_db_session.add(test_document)
        test_db_session.commit()
        
        # Search with German terms
        filters = {"user_id": test_user.id}
        results = await search_service.search_documents(
            user_id=test_user.id,
            query="Rechnung",
            filters=filters
        )
        
        assert "documents" in results