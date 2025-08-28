"""
Tests for API endpoints (updated for no-DB implementation).
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from src.email_parser.api.main import app

client = TestClient(app)


class TestAPIEndpoints:
    """Test API endpoint functionality."""
    
    def test_root_endpoint(self):
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "version" in data
        assert "docs" in data
    
    def test_health_check(self):
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
    
    def test_get_supported_providers(self):
        response = client.get("/api/v1/providers")
        assert response.status_code == 200
        data = response.json()
        assert "supported_providers" in data
        assert "total_parsers" in data
    
    @patch('src.email_parser.api.routes.transaction_processor')
    def test_sync_emails(self, mock_processor):
        # Mock the processor response
        mock_processor.process_emails.return_value = {
            "processed_emails": 5,
            "new_transactions": 3,
            "errors": 0,
            "transactions": []
        }
        
        response = client.post("/api/v1/sync")
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Email sync completed"
        assert "results" in data
        mock_processor.process_emails.assert_called_once_with(None)
    
    @patch('src.email_parser.api.routes.transaction_processor')
    def test_sync_emails_with_limit(self, mock_processor):
        mock_processor.process_emails.return_value = {
            "processed_emails": 10,
            "new_transactions": 5,
            "errors": 0,
            "transactions": []
        }
        response = client.post("/api/v1/sync?limit=10")
        assert response.status_code == 200
        mock_processor.process_emails.assert_called_once_with(10)
    
    @patch('src.email_parser.api.routes.transaction_processor')
    def test_get_status(self, mock_processor):
        # status endpoint is static in routes
        response = client.get("/api/v1/status")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "running"
        assert data["version"] == "1.0.0"
    
    @patch('src.email_parser.api.routes.transaction_processor')
    def test_get_stats(self, mock_processor):
        mock_processor.get_processing_stats.return_value = {
            "mailbox_info": {
                "total_messages": 100,
                "unread_messages": 25,
                "read_messages": 75
            },
            "supported_parsers": ["cashapp"],
            "total_parsers": 1
        }
        response = client.get("/api/v1/stats")
        assert response.status_code == 200
        data = response.json()
        assert "mailbox_info" in data
        assert "supported_parsers" in data
        assert data["total_parsers"] == 1


class TestSyncEndpoints:
    """Tests for sync endpoints that no longer persist to a DB."""

    @patch('src.email_parser.api.routes.transaction_processor')
    def test_sync_emails_by_sender(self, mock_processor):
        mock_processor.process_emails_by_sender.return_value = {
            "processed_emails": 2,
            "new_transactions": 1,
            "errors": 0,
            "transactions": [
                {"transaction_id": "tx1", "amount": 10, "email_date": "2025-08-28T12:34:56"}
            ],
            "duplicate_transactions": [],
            "message": "Successfully processed 1 new transactions"
        }

        response = client.post("/api/v1/sync/sender/cash@square.com")
        assert response.status_code == 200
        data = response.json()
        assert data["processed_emails"] == 2
        assert data["new_transactions"] == 1
        assert len(data["transactions"]) == 1
        assert data["transactions"][0]["transaction_date"] == "2025-08-28T12:34:56"
        mock_processor.process_emails_by_sender.assert_called_once_with("cash@square.com", None)

    @patch('src.email_parser.api.routes.transaction_processor')
    def test_sync_emails_by_content(self, mock_processor):
        mock_processor.process_emails_by_content.return_value = {
            "processed_emails": 1,
            "new_transactions": 1,
            "errors": 0,
            "transactions": [
                {"transaction_id": "tx2", "amount": 20, "email_date": "2025-08-28T09:10:11"}
            ],
            "duplicate_transactions": [],
            "message": "Successfully processed 1 new transactions"
        }

        response = client.post("/api/v1/sync/content/test")
        assert response.status_code == 200
        data = response.json()
        assert data["processed_emails"] == 1
        assert data["transactions"][0]["transaction_date"] == "2025-08-28T09:10:11"
        mock_processor.process_emails_by_content.assert_called_once_with("test", None)

    @patch('src.email_parser.api.routes.transaction_processor')
    def test_processor_error_handling(self, mock_processor):
        mock_processor.process_emails.side_effect = Exception("Processing failed")
        response = client.post("/api/v1/sync")
        assert response.status_code == 500
        assert "Sync failed" in response.json()["detail"]


class TestValidation:
    def test_invalid_limit_parameter(self):
        response = client.post("/api/v1/sync?limit=0")
        assert response.status_code == 422
        response = client.post("/api/v1/sync?limit=1001")
        assert response.status_code == 422
