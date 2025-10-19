"""
API routes for the Email Transaction Parser (DB interactions removed).
"""
import logging
from fastapi import APIRouter, HTTPException, Query, Header, Depends
from typing import List, Optional
from datetime import datetime, date

from config.settings import settings

from ..core.transaction_processor import TransactionProcessor
from ..core.multi_account_transaction_processor import MultiAccountTransactionProcessor
from ..core.supabase_sync import SupabaseTransactionSync

logger = logging.getLogger(__name__)

router = APIRouter()
transaction_processor = TransactionProcessor()
multi_account_processor = MultiAccountTransactionProcessor()

# Initialize Supabase sync lazily to avoid startup issues
_supabase_sync_instance = None

def get_supabase_sync():
    """Get or create Supabase sync instance."""
    global _supabase_sync_instance
    if _supabase_sync_instance is None:
        logger.info("🚀 Creating SupabaseTransactionSync instance...")
        _supabase_sync_instance = SupabaseTransactionSync()
        logger.info("✅ SupabaseTransactionSync instance created")
    return _supabase_sync_instance


def verify_batch_api_key(x_api_key: Optional[str] = Header(None)):
    """
    Verify API key for batch job endpoints.
    
    Args:
        x_api_key: API key from X-API-Key header
        
    Raises:
        HTTPException: If API key is invalid or missing
    """
    # If no API key is configured, allow access (backward compatibility)
    if not settings.batch_job_api_key:
        return True
    
    # If API key is configured, require it
    if not x_api_key:
        raise HTTPException(
            status_code=401, 
            detail="API key required. Provide X-API-Key header."
        )
    
    if x_api_key != settings.batch_job_api_key:
        raise HTTPException(
            status_code=403, 
            detail="Invalid API key"
        )
    
    return True


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


@router.get("/debug/integrations")
async def debug_integrations():
    """
    DEBUG ENDPOINT: Check what OAuth integrations are found in Supabase.
    
    This helps diagnose why no transactions are being found.
    """
    from ..core.email_integration_manager import EmailIntegrationManager
    
    try:
        integration_manager = EmailIntegrationManager()
        integrations = integration_manager.get_active_oauth_integrations()
        
        integration_info = []
        for integration in integrations:
            integration_info.append({
                "integration_id": integration.id,
                "user_id": integration.user_id,
                "email_username": integration.email_username,
                "oauth_provider": integration.oauth_provider,
                "has_access_token": bool(integration.oauth_access_token),
                "has_refresh_token": bool(integration.oauth_refresh_token),
                "token_expiry": str(integration.oauth_token_expiry) if integration.oauth_token_expiry else None,
                "is_active": integration.is_active
            })
        
        return {
            "supabase_connected": True,
            "total_integrations_found": len(integrations),
            "integrations": integration_info,
            "message": f"Found {len(integrations)} active OAuth integrations in Supabase"
        }
        
    except Exception as e:
        import traceback
        return {
            "supabase_connected": False,
            "error": str(e),
            "traceback": traceback.format_exc(),
            "message": "Failed to connect to Supabase or fetch integrations"
        }


@router.get("/status")
async def status_check():
    """Status check endpoint."""
    return {"status": "running", "version": "1.0.0"}


@router.get("/stats")
async def get_stats():
    """Get processing statistics (email client + parsers)."""
    return transaction_processor.get_processing_stats()


@router.get("/providers")
async def get_supported_providers():
    """
    Get list of supported email providers/parsers.
    """
    return {
        "supported_providers": transaction_processor.parser_factory.list_supported_providers(),
        "total_parsers": len(transaction_processor.parser_factory.get_all_parsers())
    }


@router.post("/sync")
async def sync_emails(
    limit: Optional[int] = Query(None, ge=1, le=1000, description="Maximum emails to process")
):
    """
    Sync emails and extract transactions (no DB storage).
    """
    try:
        results = transaction_processor.process_emails(limit)
        return {
            "message": "Email sync completed",
            "results": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")


@router.post("/sync/sender/{sender_email}")
async def sync_emails_by_sender(
    sender_email: str,
    limit: Optional[int] = Query(None, ge=0, description="Number of emails to process (0 = all emails)")
):
    """Sync emails from a specific sender across all Supabase OAuth integrations and return parsed transactions."""
    # Use multi-account processor to fetch from Supabase integrations
    result = multi_account_processor.process_emails_by_sender(sender_email, limit)

    # Return clean transaction data with all fields for staging.pay_transactions
    clean_transactions = []
    for transaction in result.get("transactions", []):
        # Format transaction data for staging.pay_transactions table
        clean_transactions.append({
            # Required fields for staging.pay_transactions
            "amount_paid": transaction.get("amount"),
            "paid_by": transaction.get("sender"),
            "paid_to": transaction.get("recipient"),
            "payment_status": transaction.get("status", "completed"),
            "transaction_number": transaction.get("cashapp_transaction_number") or transaction.get("transaction_id"),
            "transaction_date": transaction.get("email_date"),
            
            # Additional metadata
            "user_id": transaction.get("integration_user_id"),  # From api.email_integrations
            "integration_id": transaction.get("integration_id"),
            "currency": transaction.get("currency", "USD"),
            "transaction_type": transaction.get("transaction_type"),
            "deposited_to": transaction.get("deposited_to"),
            "source_provider": transaction.get("source_provider", "cashapp")
        })

    return {
        "processed_emails": result.get("processed_emails", 0),
        "new_transactions": result.get("new_transactions", 0),
        "errors": result.get("errors", 0),
        "transactions": clean_transactions,
        "duplicate_transactions": result.get("duplicate_transactions", []),
        "message": result.get("message", ""),
        "Erros": result.get("Erros", [])
    }


@router.post("/sync/sender/{sender_email}/date-range")
async def sync_emails_by_sender_date_range(
    sender_email: str,
    start_date: date = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date (YYYY-MM-DD), optional")
):
    """Sync emails from a specific sender within a date range across all Supabase OAuth integrations."""
    # Create timezone-aware datetimes
    from datetime import timezone
    start_datetime = datetime.combine(start_date, datetime.min.time()).replace(tzinfo=timezone.utc)
    end_datetime = datetime.combine(end_date if end_date else start_date, datetime.max.time()).replace(tzinfo=timezone.utc)
    
    # Use multi-account processor to fetch from Supabase integrations
    result = multi_account_processor.process_emails_by_sender_date_range(
        sender_email,
        start_datetime,
        end_datetime
    )

    # Return clean transaction data with all fields for staging.pay_transactions
    clean_transactions = []
    for transaction in result.get("transactions", []):
        # Format transaction data for staging.pay_transactions table
        clean_transactions.append({
            # Required fields for staging.pay_transactions
            "amount_paid": transaction.get("amount"),
            "paid_by": transaction.get("sender"),
            "paid_to": transaction.get("recipient"),
            "payment_status": transaction.get("status", "completed"),
            "transaction_number": transaction.get("cashapp_transaction_number") or transaction.get("transaction_id"),
            "transaction_date": transaction.get("email_date"),
            
            # Additional metadata
            "user_id": transaction.get("integration_user_id"),  # From api.email_integrations
            "integration_id": transaction.get("integration_id"),
            "currency": transaction.get("currency", "USD"),
            "transaction_type": transaction.get("transaction_type"),
            "deposited_to": transaction.get("deposited_to"),
            "source_provider": transaction.get("source_provider", "cashapp")
        })

    return {
        "processed_emails": result.get("processed_emails", 0),
        "new_transactions": result.get("new_transactions", 0),
        "errors": result.get("errors", 0),
        "transactions": clean_transactions,
        "duplicate_transactions": result.get("duplicate_transactions", []),
        "message": result.get("message", ""),
        "Erros": result.get("Erros", [])
    }


@router.post("/sync/content/{search_text}")
async def sync_emails_by_content(
    search_text: str,
    limit: Optional[int] = Query(None, ge=0, description="Number of emails to process (0 = all emails)")
):
    """Sync emails containing specific text and return parsed transactions (no DB)."""
    processor = TransactionProcessor()
    result = processor.process_emails_by_content(search_text, limit)

    clean_transactions = []
    for transaction in result.get("transactions", []):
        recipient = transaction.get("recipient", "")
        if recipient and recipient.lower() == "blockchain realty".lower():
            clean_transactions.append({
                "amount_paid": transaction.get("amount"),
                "paid_by": transaction.get("sender"),
                "paid_to": recipient,
                "payment_status": transaction.get("status"),
                "deposited_to": transaction.get("deposited_to"),
                "transaction_number": transaction.get("transaction_id"),
                "transaction_date": transaction.get("email_date"),
                "currency": transaction.get("currency"),
                "transaction_type": transaction.get("transaction_type")
            })

    return {
        "processed_emails": result.get("processed_emails", 0),
        "new_transactions": result.get("new_transactions", 0),
        "errors": result.get("errors", 0),
        "transactions": clean_transactions,
        "duplicate_transactions": result.get("duplicate_transactions", []),
        "message": result.get("message", ""),
        "Erros": result.get("Erros", [])
    }


@router.post("/sync/content/{search_text}/date-range")
async def sync_emails_by_content_date_range(
    search_text: str,
    start_date: date = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date (YYYY-MM-DD), optional")
):
    """Sync emails containing specific text within a date range and return parsed transactions."""
    processor = TransactionProcessor()
    result = processor.process_emails_by_content_date_range(
        search_text,
        datetime.combine(start_date, datetime.min.time()),
        datetime.combine(end_date, datetime.max.time()) if end_date else None
    )

    clean_transactions = []
    for transaction in result.get("transactions", []):
        recipient = transaction.get("recipient", "")
        if recipient and recipient.lower() == "blockchain realty".lower():
            clean_transactions.append({
                "amount_paid": transaction.get("amount"),
                "paid_by": transaction.get("sender"),
                "paid_to": recipient,
                "payment_status": transaction.get("status"),
                "deposited_to": transaction.get("deposited_to"),
                "transaction_number": transaction.get("transaction_id"),
                "transaction_date": transaction.get("email_date"),
                "currency": transaction.get("currency"),
                "transaction_type": transaction.get("transaction_type")
            })

    return {
        "processed_emails": result.get("processed_emails", 0),
        "new_transactions": result.get("new_transactions", 0),
        "errors": result.get("errors", 0),
        "transactions": clean_transactions,
        "duplicate_transactions": result.get("duplicate_transactions", []),
        "message": result.get("message", ""),
        "Erros": result.get("Erros", [])
    }


@router.post("/sync/subject/{search_text}")
async def sync_emails_by_subject(
    search_text: str,
    limit: Optional[int] = Query(None, ge=0, description="Number of emails to process (0 = all emails)")
):
    """Sync emails by subject and return parsed transactions (no DB)."""
    processor = TransactionProcessor()
    result = processor.process_emails_by_subject(search_text, limit)

    clean_transactions = []
    for transaction in result.get("transactions", []):
        recipient = transaction.get("recipient", "")
        if recipient and recipient.lower() == "blockchain realty".lower():
            clean_transactions.append({
                "amount_paid": transaction.get("amount"),
                "paid_by": transaction.get("sender"),
                "paid_to": recipient,
                "payment_status": transaction.get("status"),
                "deposited_to": transaction.get("deposited_to"),
                "transaction_number": transaction.get("transaction_id"),
                "transaction_date": transaction.get("email_date"),
                "currency": transaction.get("currency"),
                "transaction_type": transaction.get("transaction_type")
            })

    return {
        "processed_emails": result.get("processed_emails", 0),
        "new_transactions": result.get("new_transactions", 0),
        "errors": result.get("errors", 0),
        "transactions": clean_transactions,
        "duplicate_transactions": result.get("duplicate_transactions", []),
        "message": result.get("message", ""),
        "Erros": result.get("Erros", [])
    }


# ========== BATCH JOB ENDPOINTS (Auto-insert to Supabase) ==========

@router.post("/batch/sync-and-store/sender/{sender_email}")
async def batch_sync_and_store_by_sender(
    sender_email: str,
    limit: Optional[int] = Query(None, ge=0, description="Number of emails to process per account (0 = all)"),
    _: bool = Depends(verify_batch_api_key)
):
    """
    BATCH JOB ENDPOINT: Sync emails from sender and automatically insert into staging.pay_transactions.
    
    This endpoint:
    1. Fetches all active OAuth integrations from api.email_integrations
    2. Processes emails from the specified sender across all Gmail accounts
    3. Automatically inserts transactions into staging.pay_transactions
    4. Returns processing summary
    
    Use this for scheduled daily batch jobs.
    """
    try:
        # Process emails from all integrations
        result = multi_account_processor.process_emails_by_sender(sender_email, limit)
        
        # Insert into Supabase staging.pay_transactions
        insert_result = get_supabase_sync().insert_transactions(result.get("transactions", []))
        
        return {
            "batch_job": "sync-and-store",
            "sender_email": sender_email,
            "processed_emails": result.get("processed_emails", 0),
            "parsed_transactions": result.get("new_transactions", 0),
            "parsing_errors": result.get("errors", 0),
            
            # Supabase insert results
            "inserted_to_supabase": insert_result.get("inserted_count", 0),
            "duplicates_skipped": insert_result.get("duplicate_count", 0),
            "insert_errors": insert_result.get("error_count", 0),
            "insert_error_details": insert_result.get("errors", []),
            
            "message": f"Processed {result.get('new_transactions', 0)} transactions, inserted {insert_result.get('inserted_count', 0)} into Supabase",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Batch job failed: {e}")
        raise HTTPException(status_code=500, detail=f"Batch job failed: {str(e)}")


@router.post("/batch/sync-and-store/sender/{sender_email}/date-range")
async def batch_sync_and_store_by_sender_date_range(
    sender_email: str,
    start_date: date = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date (YYYY-MM-DD), optional"),
    _: bool = Depends(verify_batch_api_key)
):
    """
    BATCH JOB ENDPOINT: Sync emails from sender in date range and auto-insert to staging.pay_transactions.
    
    This endpoint:
    1. Fetches all active OAuth integrations from api.email_integrations
    2. Processes emails from the specified sender in date range across all Gmail accounts
    3. Automatically inserts transactions into staging.pay_transactions
    4. Returns processing summary
    
    Use this for scheduled batch jobs with specific date ranges.
    """
    try:
        # Create timezone-aware datetimes
        from datetime import timezone
        start_datetime = datetime.combine(start_date, datetime.min.time()).replace(tzinfo=timezone.utc)
        end_datetime = datetime.combine(end_date if end_date else start_date, datetime.max.time()).replace(tzinfo=timezone.utc)
        
        # Process emails from all integrations
        result = multi_account_processor.process_emails_by_sender_date_range(
            sender_email,
            start_datetime,
            end_datetime
        )
        
        # Insert into Supabase staging.pay_transactions
        insert_result = get_supabase_sync().insert_transactions(result.get("transactions", []))
        
        return {
            "batch_job": "sync-and-store-date-range",
            "sender_email": sender_email,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat() if end_date else None,
            "processed_emails": result.get("processed_emails", 0),
            "parsed_transactions": result.get("new_transactions", 0),
            "parsing_errors": result.get("errors", 0),
            
            # Supabase insert results
            "inserted_to_supabase": insert_result.get("inserted_count", 0),
            "duplicates_skipped": insert_result.get("duplicate_count", 0),
            "insert_errors": insert_result.get("error_count", 0),
            "insert_error_details": insert_result.get("errors", []),
            
            "message": f"Processed {result.get('new_transactions', 0)} transactions, inserted {insert_result.get('inserted_count', 0)} into Supabase",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Batch job failed: {e}")
        raise HTTPException(status_code=500, detail=f"Batch job failed: {str(e)}")


@router.post("/batch/daily-sync")
async def batch_daily_sync(
    target_date: Optional[date] = Query(None, description="Date to process (YYYY-MM-DD), defaults to today"),
    _: bool = Depends(verify_batch_api_key)
):
    """
    MAIN BATCH JOB ENDPOINT: Process all OAuth integrations for a specific day.
    
    This endpoint:
    1. Fetches all active OAuth integrations from api.email_integrations
    2. For EACH integration:
       - Uses email_username as the sender to search for
       - Searches that user's Gmail inbox for payment emails from their own email
       - Processes emails for the target date (full day)
       - Automatically inserts into staging.pay_transactions
    3. Returns comprehensive processing summary
    
    Use this for scheduled daily batch jobs.
    
    Example cron:
    # Daily at 2 AM for yesterday's transactions
    0 2 * * * curl -X POST "http://localhost:8000/api/v1/batch/daily-sync"
    """
    from ..core.email_integration_manager import EmailIntegrationManager
    
    # Default to today if no date specified
    if target_date is None:
        target_date = date.today()
    
    # Set start and end time for the full day (with timezone)
    from datetime import timezone
    start_datetime = datetime.combine(target_date, datetime.min.time()).replace(tzinfo=timezone.utc)
    end_datetime = datetime.combine(target_date, datetime.max.time()).replace(tzinfo=timezone.utc)
    
    all_results = {
        "batch_job": "daily-sync",
        "target_date": target_date.isoformat(),
        "start_datetime": start_datetime.isoformat(),
        "end_datetime": end_datetime.isoformat(),
        "integrations_processed": 0,
        "total_emails_processed": 0,
        "total_transactions_parsed": 0,
        "total_inserted_to_supabase": 0,
        "total_duplicates": 0,
        "total_errors": 0,
        "integration_results": [],
        "timestamp": datetime.now().isoformat()
    }
    
    try:
        # Get all active OAuth integrations
        integration_manager = EmailIntegrationManager()
        integrations = integration_manager.get_active_oauth_integrations()
        
        if not integrations:
            logger.warning("No active OAuth integrations found")
            all_results["message"] = "No active OAuth integrations found"
            return all_results
        
        logger.info(f"Processing daily batch for {len(integrations)} OAuth integrations on {target_date}")
        
        # Process each integration
        for integration in integrations:
            try:
                # Get email_username from integration (this is the sender to search for)
                sender_email = integration.email_username
                
                if not sender_email:
                    logger.warning(f"Integration {integration.id} has no email_username, skipping")
                    all_results["total_errors"] += 1
                    all_results["integration_results"].append({
                        "integration_id": integration.id,
                        "user_id": integration.user_id,
                        "email_username": None,
                        "error": "No email_username configured"
                    })
                    continue
                
                logger.info(f"Processing integration {integration.id}: searching for emails from {sender_email}")
                
                # Refresh OAuth token if needed
                if not integration_manager.refresh_oauth_token_if_needed(integration):
                    logger.error(f"Failed to refresh OAuth token for integration {integration.id}")
                    all_results["total_errors"] += 1
                    all_results["integration_results"].append({
                        "integration_id": integration.id,
                        "user_id": integration.user_id,
                        "email_username": sender_email,
                        "error": "OAuth token refresh failed"
                    })
                    continue
                
                # Process emails from this integration for the target date
                # Search for payment emails from the user's own email address
                result = multi_account_processor.process_emails_by_sender_date_range(
                    sender_email=sender_email,
                    start_date=start_datetime,
                    end_date=end_datetime
                )
                
                # Insert into Supabase
                insert_result = get_supabase_sync().insert_transactions(result.get("transactions", []))
                
                # Aggregate results
                all_results["integrations_processed"] += 1
                all_results["total_emails_processed"] += result.get("processed_emails", 0)
                all_results["total_transactions_parsed"] += result.get("new_transactions", 0)
                all_results["total_inserted_to_supabase"] += insert_result.get("inserted_count", 0)
                all_results["total_duplicates"] += insert_result.get("duplicate_count", 0)
                all_results["total_errors"] += result.get("errors", 0) + insert_result.get("error_count", 0)
                
                # Add integration-specific results
                all_results["integration_results"].append({
                    "integration_id": integration.id,
                    "user_id": integration.user_id,
                    "email_username": sender_email,
                    "emails_processed": result.get("processed_emails", 0),
                    "transactions_parsed": result.get("new_transactions", 0),
                    "inserted_to_supabase": insert_result.get("inserted_count", 0),
                    "duplicates": insert_result.get("duplicate_count", 0),
                    "errors": result.get("errors", 0) + insert_result.get("error_count", 0)
                })
                
                # Update last sync time
                integration_manager.update_last_sync(integration.id)
                
            except Exception as e:
                logger.error(f"Error processing integration {integration.id}: {e}")
                all_results["total_errors"] += 1
                all_results["integration_results"].append({
                    "integration_id": integration.id if hasattr(integration, 'id') else None,
                    "user_id": integration.user_id if hasattr(integration, 'user_id') else None,
                    "email_username": sender_email if 'sender_email' in locals() else None,
                    "error": str(e)
                })
        
        all_results["message"] = f"Daily batch complete: Processed {all_results['total_transactions_parsed']} transactions, inserted {all_results['total_inserted_to_supabase']} into Supabase"
        
        logger.info(f"Daily batch job complete: {all_results}")
        return all_results
        
    except Exception as e:
        logger.error(f"Daily batch job failed: {e}")
        raise HTTPException(status_code=500, detail=f"Daily batch job failed: {str(e)}")
