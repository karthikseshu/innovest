"""
API routes for the Email Transaction Parser (DB interactions removed).
"""
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from datetime import datetime, date

from ..core.transaction_processor import TransactionProcessor

router = APIRouter()
transaction_processor = TransactionProcessor()


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


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
    """Sync emails from a specific sender and return parsed transactions (no DB)."""
    processor = TransactionProcessor()
    result = processor.process_emails_by_sender(sender_email, limit)

    # Return clean transaction data
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


@router.post("/sync/sender/{sender_email}/date-range")
async def sync_emails_by_sender_date_range(
    sender_email: str,
    start_date: date = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date (YYYY-MM-DD), optional")
):
    """Sync emails from a specific sender within a date range and return parsed transactions."""
    processor = TransactionProcessor()
    result = processor.process_emails_by_sender_date_range(
        sender_email,
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
