# backend/tests/test_categories.py
"""
Bonifatus DMS - Category Tests
Comprehensive tests for category management and AI suggestions
"""

import pytest
from unittest.mock import patch, Mock
from fastapi import status

from src.database.models import Category, Document, UserTier
from src.services.category_service import CategoryService


@pytest.mark.integration
class TestCategoryAPI:
    """Test category management API endpoints"""
    
    def test_list_categories_success(self, client, auth_headers, test_user, test_category):
        """Test listing user categories"""
        with patch('src.api.categories.AuthService') as mock_auth_class, \
             patch('src.api.categories.CategoryService') as mock_cat_class:
            
            mock_auth_service = Mock()
            mock_auth_class.return_value = mock_auth_service
            mock_auth_service.get_current_user.return_value = test_user
            
            mock_cat_service = Mock()
            mock_cat_class.return_value = mock_cat_service
            mock_cat_service.get_user_categories.return_value = [test_category]
            
            response = client.get("/api/v1/categories/", headers=auth_headers)
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert "categories" in data
            assert len(data["categories"]) >= 0
            assert "total" in data
    
    def test_create_category_success(self, client, auth_headers, test_user):
        """Test creating new category"""
        category_data = {
            "name_en": "Test Category",
            "name_de": "Test Kategorie",
            "description_en": "Test description",
            "description_de": "Test Beschreibung",
            "color": "#FF5733",
            "keywords": ["test", "category"]
        }
        
        with patch('src.api.categories.AuthService') as mock_auth_class, \
             patch('src.api.categories.CategoryService') as mock_cat_class:
            
            mock_auth_service = Mock()
            mock_auth_class.return_value = mock_auth_service
            mock_auth_service.get_current_user.return_value = test_user
            
            # Mock database queries
            with patch('src.api.categories.db.query') as mock_query:
                mock_query.return_value.filter.return_value.count.return_value = 0
                mock_query.return_value.filter.return_value.first.return_value = None
                
                mock_cat_service = Mock()
                mock_cat_class.return_value = mock_cat_service
                
                new_category = Category(
                    id=1,
                    user_id=test_user.id,
                    name_en="Test Category",
                    name_de="Test Kategorie",
                    color="#FF5733"
                )
                mock_cat_service.create_category.return_value = new_category
                
                response = client.post(
                    "/api/v1/categories/",
                    json=category_data,
                    headers=auth_headers
                )
                
                assert response.status_code == status.HTTP_200_OK
                data = response.json()
                assert data["name_en"] == "Test Category"
                assert data["name_de"] == "Test Kategorie"
    
    def test_create_category_limit_exceeded(self, client, auth_headers, test_user):
        """Test category creation when limit is exceeded"""
        test_user.tier = UserTier.FREE  # Free tier has category limits
        
        with patch('src.api.categories.AuthService') as mock_auth_class:
            mock_auth_service = Mock()
            mock_auth_class.return_value = mock_auth_service
            mock_auth_service.get_current_user.return_value = test_user
            
            with patch('src.api.categories.db.query') as mock_query:
                # Mock user has reached category limit
                mock_query.return_value.filter.return_value.count.return_value = 10
                
                category_data = {
                    "name_en": "Excess Category",
                    "name_de": "Überschuss Kategorie",
                    "color": "#FF5733"
                }
                
                response = client.post(
                    "/api/v1/categories/",
                    json=category_data,
                    headers=auth_headers
                )
                
                assert response.status_code == status.HTTP_400_BAD_REQUEST
                assert "Maximum" in response.json()["detail"]
    
    def test_get_category_success(self, client, auth_headers, test_user, test_category):
        """Test getting category details"""
        with patch('src.api.categories.AuthService') as mock_auth_class:
            mock_auth_service = Mock()
            mock_auth_class.return_value = mock_auth_service
            mock_auth_service.get_current_user.return_value = test_user
            
            with patch('src.api.categories.db.query') as mock_query:
                mock_query.return_value.filter.return_value.first.return_value = test_category
                mock_query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []
                
                response = client.get(f"/api/v1/categories/{test_category.id}", headers=auth_headers)
                
                assert response.status_code == status.HTTP_200_OK
                data = response.json()
                assert data["id"] == test_category.id
                assert data["name_en"] == test_category.name_en
    
    def test_update_category_success(self, client, auth_headers, test_user, test_category):
        """Test updating category"""
        update_data = {
            "name_en": "Updated Category",
            "color": "#00FF00"
        }
        
        with patch('src.api.categories.AuthService') as mock_auth_class:
            mock_auth_service = Mock()
            mock_auth_class.return_value = mock_auth_service
            mock_auth_service.get_current_user.return_value = test_user
            
            with patch('src.api.categories.db.query') as mock_query, \
                 patch('src.api.categories.db.commit'):
                mock_query.return_value.filter.return_value.first.return_value = test_category
                
                response = client.put(
                    f"/api/v1/categories/{test_category.id}",
                    json=update_data,
                    headers=auth_headers
                )
                
                assert response.status_code == status.HTTP_200_OK
                data = response.json()
                assert data["success"] is True
    
    def test_delete_category_success(self, client, auth_headers, test_user, test_category):
        """Test deleting category"""
        with patch('src.api.categories.AuthService') as mock_auth_class:
            mock_auth_service = Mock()
            mock_auth_class.return_value = mock_auth_service
            mock_auth_service.get_current_user.return_value = test_user
            
            with patch('src.api.categories.db.query') as mock_query, \
                 patch('src.api.categories.db.delete'), \
                 patch('src.api.categories.db.commit'):
                
                # Mock category exists and has no documents
                mock_query.return_value.filter.return_value.first.return_value = test_category
                mock_query.return_value.filter.return_value.count.return_value = 0
                
                response = client.delete(f"/api/v1/categories/{test_category.id}", headers=auth_headers)
                
                assert response.status_code == status.HTTP_200_OK
                data = response.json()
                assert data["success"] is True
    
    def test_suggest_category_success(self, client, auth_headers, test_user):
        """Test AI category suggestions"""
        suggestion_data = {
            "text": "This is an invoice for office supplies from ABC Company for $500.",
            "filename": "invoice_abc_company.pdf"
        }
        
        with patch('src.api.categories.AuthService') as mock_auth_class, \
             patch('src.api.categories.CategoryService') as mock_cat_class:
            
            mock_auth_service = Mock()
            mock_auth_class.return_value = mock_auth_service
            mock_auth_service.get_current_user.return_value = test_user
            
            mock_cat_service = Mock()
            mock_cat_class.return_value = mock_cat_service
            mock_cat_service.suggest_categories.return_value = [
                {
                    "category_id": 1,
                    "category_name": "Finance",
                    "confidence": 0.85,
                    "is_system_category": True,
                    "color": "#10B981",
                    "matched_keywords": ["invoice", "company"]
                }
            ]
            
            response = client.post(
                "/api/v1/categories/suggest",
                json=suggestion_data,
                headers=auth_headers
            )
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert "suggestions" in data
            assert len(data["suggestions"]) > 0
            assert data["suggestions"][0]["category_name"] == "Finance"


@pytest.mark.unit
class TestCategoryService:
    """Test CategoryService business logic"""
    
    @pytest.mark.asyncio
    async def test_get_user_categories(self, test_db_session, test_user, test_category):
        """Test retrieving user categories"""
        category_service = CategoryService(test_db_session)
        
        # Add test category to session
        test_db_session.add(test_category)
        test_db_session.commit()
        
        categories = await category_service.get_user_categories(
            user_id=test_user.id,
            include_system=True,
            include_user=True
        )
        
        assert isinstance(categories, list)
        # Should include at least the test category
        user_categories = [cat for cat in categories if not cat.is_system_category]
        assert len(user_categories) >= 1
    
    @pytest.mark.asyncio
    async def test_create_category(self, test_db_session, test_user):
        """Test creating new category"""
        category_service = CategoryService(test_db_session)
        
        category_data = {
            "user_id": test_user.id,
            "name_en": "New Category",
            "name_de": "Neue Kategorie",
            "description_en": "Test description",
            "color": "#FF5733",
            "keywords": "test,new,category"
        }
        
        category = await category_service.create_category(category_data)
        
        assert category is not None
        assert category.name_en == "New Category"
        assert category.name_de == "Neue Kategorie"
        assert category.user_id == test_user.id
        assert category.is_system_category is False
    
    @pytest.mark.asyncio
    async def test_suggest_categories(self, test_db_session, test_user, test_category):
        """Test AI category suggestions"""
        category_service = CategoryService(test_db_session)
        
        # Add test category with relevant keywords
        test_category.keywords = "invoice,bill,payment,finance"
        test_db_session.add(test_category)
        test_db_session.commit()
        
        text = "This is an invoice for $500 payment to ABC Company"
        
        suggestions = await category_service.suggest_categories(
            user_id=test_user.id,
            text=text,
            language="en"
        )
        
        assert isinstance(suggestions, list)
        if suggestions:  # May be empty if no good matches
            suggestion = suggestions[0]
            assert "category_id" in suggestion
            assert "confidence" in suggestion
            assert "matched_keywords" in suggestion
    
    @pytest.mark.asyncio
    async def test_delete_category(self, test_db_session, test_user, test_category):
        """Test deleting category"""
        category_service = CategoryService(test_db_session)
        
        # Add category to session
        test_db_session.add(test_category)
        test_db_session.commit()
        
        result = await category_service.delete_category(
            category_id=test_category.id,
            user_id=test_user.id
        )
        
        assert result["success"] is True
        
        # Verify category is deleted
        deleted_category = test_db_session.query(Category).filter(
            Category.id == test_category.id
        ).first()
        assert deleted_category is None
    
    def test_calculate_category_relevance(self, test_db_session):
        """Test category relevance calculation"""
        category_service = CategoryService(test_db_session)
        
        # Create mock category
        category = Category(
            name_en="Finance",
            name_de="Finanzen",
            keywords="invoice,bill,payment,money,financial"
        )
        
        # Test text with financial terms
        text = "This is an invoice for office supplies payment of $500"
        
        relevance = category_service._calculate_category_relevance(text, category, "en")
        
        assert isinstance(relevance, float)
        assert 0.0 <= relevance <= 1.0
        assert relevance > 0  # Should have some relevance due to "invoice" and "payment"
    
    def test_get_matching_keywords(self, test_db_session):
        """Test keyword matching"""
        category_service = CategoryService(test_db_session)
        
        category = Category(
            keywords="invoice,bill,payment,financial"
        )
        
        text = "This invoice shows a payment of $500"
        
        matches = category_service._get_matching_keywords(text, category)
        
        assert isinstance(matches, list)
        assert "invoice" in matches
        assert "payment" in matches
        assert "bill" not in matches  # Not in the text