"""
Supabase configuration and client setup.
"""
import os
import logging
from dotenv import load_dotenv
from supabase import create_client, Client
from supabase.lib.client_options import ClientOptions
from typing import Optional

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)

# Supabase configuration from innovest-ai project
SUPABASE_URL = "https://dshlixmkpqpdnnixkykl.supabase.co"
SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImRzaGxpeG1rcHFwZG5uaXhreWtsIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTU0NzgwODMsImV4cCI6MjA3MTA1NDA4M30.aWf8ShUJgs36CxWIF3pUFsUoDz1hpzKO8wKzfHcuyPs"

# Service role key for admin operations (must be set via environment variable)
SUPABASE_SERVICE_ROLE_KEY = os.environ.get('SUPABASE_SERVICE_ROLE_KEY')

logger.info(f"Supabase URL: {SUPABASE_URL}")
logger.info(f"Service role key configured: {bool(SUPABASE_SERVICE_ROLE_KEY)}")
if SUPABASE_SERVICE_ROLE_KEY:
    logger.info(f"Service role key length: {len(SUPABASE_SERVICE_ROLE_KEY)}")
else:
    logger.warning("⚠️  SUPABASE_SERVICE_ROLE_KEY not found in environment!")


class SupabaseClient:
    """Wrapper for Supabase client with api schema configuration."""
    
    def __init__(self, use_service_role: bool = False):
        """
        Initialize Supabase client.
        
        Args:
            use_service_role: If True, use service role key for admin operations
        """
        key = SUPABASE_SERVICE_ROLE_KEY if use_service_role and SUPABASE_SERVICE_ROLE_KEY else SUPABASE_ANON_KEY
        
        # Create client with 'api' schema configuration
        options = ClientOptions(schema='api')
        self.client: Client = create_client(SUPABASE_URL, key, options=options)
    
    def get_client(self) -> Client:
        """Get the Supabase client instance."""
        return self.client


# Create singleton instances for different schemas
_api_schema_client: Optional[Client] = None
_staging_schema_client: Optional[Client] = None


def get_supabase_client(use_service_role: bool = True, schema: str = 'staging') -> Client:
    """
    Get a Supabase client instance.
    
    Args:
        use_service_role: If True, use service role key for admin operations
        schema: Database schema to use ('api' or 'staging')
        
    Returns:
        Supabase client instance
    """
    key = SUPABASE_SERVICE_ROLE_KEY if use_service_role and SUPABASE_SERVICE_ROLE_KEY else SUPABASE_ANON_KEY
    
    logger.info(f"Creating Supabase client: use_service_role={use_service_role}, schema={schema}")
    logger.info(f"Using service role: {use_service_role and bool(SUPABASE_SERVICE_ROLE_KEY)}")
    logger.info(f"Key starts with: {key[:20]}..." if key else "No key!")
    
    # Create fresh client each time to avoid singleton issues
    try:
        options = ClientOptions(schema=schema)
        logger.info(f"Creating client with options: {options}")
        logger.info(f"Schema in options: {getattr(options, 'schema', 'unknown')}")
        
        client = create_client(SUPABASE_URL, key, options=options)
        logger.info(f"Created fresh {schema} schema client")
        
        # Log client creation success
        logger.info(f"✅ Client created successfully for schema: {schema}")
        
        return client
    except Exception as e:
        logger.error(f"❌ Failed to create client for schema {schema}: {e}")
        raise

