"""
Supabase sync module for inserting transactions into staging.pay_transactions.
"""
import logging
from typing import List, Dict, Any
from config.supabase import get_supabase_client

logger = logging.getLogger(__name__)
logger.info("📦 SupabaseTransactionSync module imported")


class SupabaseTransactionSync:
    """Handles syncing transactions to Supabase staging.pay_transactions table."""
    
    def __init__(self):
        """Initialize Supabase sync client."""
        logger.info("🚀 Initializing SupabaseTransactionSync...")
        # Use staging schema for pay_transactions table
        self.supabase = get_supabase_client(use_service_role=True, schema='staging')
        logger.info(f"Supabase sync client initialized with schema: staging")
        
        # Client is ready for use
        logger.info(f"Supabase client ready for staging schema operations")
    
    def insert_transactions(
        self, 
        transactions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Insert transactions into staging.pay_transactions table.
        
        Args:
            transactions: List of transaction dictionaries from email parser
            
        Returns:
            Dictionary with insert results and statistics
        """
        if not transactions:
            logger.info("No transactions to insert")
            return {
                "inserted_count": 0,
                "duplicate_count": 0,
                "error_count": 0,
                "errors": []
            }
        
        inserted_count = 0
        duplicate_count = 0
        error_count = 0
        errors = []
        
        # Test staging schema access first
        try:
            logger.info("Testing staging schema access...")
            logger.info(f"Supabase client type: {type(self.supabase)}")
            logger.info(f"Supabase client URL: {getattr(self.supabase, 'url', 'unknown')}")
            
            test_result = self.supabase.table('pay_transactions').select('*').limit(1).execute()
            logger.info(f"✅ Staging schema access successful: {len(test_result.data)} records found")
        except Exception as e:
            logger.error(f"❌ Staging schema access failed: {e}")
            logger.error(f"Error type: {type(e)}")
            logger.error(f"Error details: {e}")
            return {
                'inserted_count': 0,
                'duplicate_count': 0,
                'error_count': len(transactions),
                'errors': [{'transaction_number': 'schema_test', 'error': str(e)}],
                'message': f'Staging schema access failed: {e}'
            }
        
        logger.info(f"Attempting to insert {len(transactions)} transactions into Supabase")
        
        for transaction in transactions:
            try:
                # Prepare data for staging.pay_transactions
                payment_status = transaction.get('payment_status', 'completed')
                if payment_status:
                    payment_status = payment_status.lower()
                
                transaction_data = {
                    'user_id': transaction.get('integration_user_id'),
                    'amount_paid': transaction.get('amount_paid') or transaction.get('amount'),
                    'paid_by': transaction.get('paid_by') or transaction.get('sender'),
                    'paid_to': transaction.get('paid_to') or transaction.get('recipient'),
                    'payment_status': payment_status,
                    'transaction_number': transaction.get('transaction_number') or transaction.get('cashapp_transaction_number') or transaction.get('transaction_id'),
                    'transaction_date': transaction.get('transaction_date') or transaction.get('email_date'),
                    'payment_provider': transaction.get('source_provider', 'cashapp'),
                    'source': 'email-reader-api',
                    'raw_data': transaction,
                    'created_by': transaction.get('integration_user_id'),
                    'updated_by': transaction.get('integration_user_id')
                }
                
                # Validate required fields
                if not transaction_data['user_id']:
                    error_count += 1
                    errors.append({
                        'transaction_number': transaction_data['transaction_number'],
                        'error': 'Missing user_id'
                    })
                    continue
                
                if not transaction_data['amount_paid'] or transaction_data['amount_paid'] <= 0:
                    error_count += 1
                    errors.append({
                        'transaction_number': transaction_data['transaction_number'],
                        'error': 'Invalid amount_paid'
                    })
                    continue
                
                # Insert into Supabase
                logger.info(f"Inserting transaction: {transaction_data['transaction_number']}")
                logger.info(f"Using Supabase client for staging schema")
                
                # Use staging schema table
                result = self.supabase.table('pay_transactions').insert(transaction_data).execute()
                
                if result.data:
                    inserted_count += 1
                    logger.info(f"Successfully inserted transaction: {transaction_data['transaction_number']}")
                else:
                    error_count += 1
                    errors.append({
                        'transaction_number': transaction_data['transaction_number'],
                        'error': 'No data returned from insert'
                    })
                    
            except Exception as e:
                error_msg = str(e)
                
                # Check if it's a duplicate key error
                if 'duplicate key' in error_msg.lower() or 'unique constraint' in error_msg.lower():
                    duplicate_count += 1
                    logger.info(f"Duplicate transaction skipped: {transaction_data.get('transaction_number')}")
                else:
                    error_count += 1
                    errors.append({
                        'transaction_number': transaction_data.get('transaction_number', 'unknown'),
                        'error': error_msg
                    })
                    logger.error(f"Error inserting transaction: {error_msg}")
        
        result_summary = {
            "inserted_count": inserted_count,
            "duplicate_count": duplicate_count,
            "error_count": error_count,
            "errors": errors
        }
        
        logger.info(f"Insert summary: {result_summary}")
        return result_summary
    
    def upsert_transactions(
        self, 
        transactions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Upsert transactions (insert or update if exists) into staging.pay_transactions.
        
        Args:
            transactions: List of transaction dictionaries from email parser
            
        Returns:
            Dictionary with upsert results and statistics
        """
        if not transactions:
            logger.info("No transactions to upsert")
            return {
                "upserted_count": 0,
                "error_count": 0,
                "errors": []
            }
        
        upserted_count = 0
        error_count = 0
        errors = []
        
        logger.info(f"Attempting to upsert {len(transactions)} transactions into Supabase")
        
        # Prepare all transactions
        transactions_to_upsert = []
        
        for transaction in transactions:
            try:
                payment_status = transaction.get('payment_status', 'completed')
                if payment_status:
                    payment_status = payment_status.lower()
                
                transaction_data = {
                    'user_id': transaction.get('integration_user_id'),
                    'amount_paid': transaction.get('amount_paid') or transaction.get('amount'),
                    'paid_by': transaction.get('paid_by') or transaction.get('sender'),
                    'paid_to': transaction.get('paid_to') or transaction.get('recipient'),
                    'payment_status': payment_status,
                    'transaction_number': transaction.get('transaction_number') or transaction.get('cashapp_transaction_number') or transaction.get('transaction_id'),
                    'transaction_date': transaction.get('transaction_date') or transaction.get('email_date'),
                    'payment_provider': transaction.get('source_provider', 'cashapp'),
                    'source': 'email-reader-api',
                    'raw_data': transaction,
                    'created_by': transaction.get('integration_user_id'),
                    'updated_by': transaction.get('integration_user_id')
                }
                
                # Validate required fields
                if not transaction_data['user_id']:
                    error_count += 1
                    errors.append({
                        'transaction_number': transaction_data['transaction_number'],
                        'error': 'Missing user_id'
                    })
                    continue
                
                if not transaction_data['amount_paid'] or transaction_data['amount_paid'] <= 0:
                    error_count += 1
                    errors.append({
                        'transaction_number': transaction_data['transaction_number'],
                        'error': 'Invalid amount_paid'
                    })
                    continue
                
                transactions_to_upsert.append(transaction_data)
                
            except Exception as e:
                error_count += 1
                errors.append({
                    'transaction_number': transaction.get('transaction_id', 'unknown'),
                    'error': str(e)
                })
        
        # Bulk upsert
        if transactions_to_upsert:
            try:
                result = self.supabase.table('pay_transactions').upsert(
                    transactions_to_upsert,
                    on_conflict='user_id,transaction_number,payment_provider'
                ).execute()
                
                if result.data:
                    upserted_count = len(result.data)
                    logger.info(f"Successfully upserted {upserted_count} transactions")
                    
            except Exception as e:
                error_count += len(transactions_to_upsert)
                errors.append({
                    'transaction_number': 'bulk_upsert',
                    'error': str(e)
                })
                logger.error(f"Bulk upsert failed: {e}")
        
        result_summary = {
            "upserted_count": upserted_count,
            "error_count": error_count,
            "errors": errors
        }
        
        logger.info(f"Upsert summary: {result_summary}")
        return result_summary

