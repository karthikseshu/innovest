"""
Transaction model for storing extracted transaction data.
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Index
from sqlalchemy.sql import func
from datetime import datetime
from typing import Optional

from .database import Base


class Transaction(Base):
    """Transaction model for storing extracted transaction data."""
    
    __tablename__ = "transactions"
    
    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(String(255), unique=True, index=True, nullable=False)
    sender = Column(String(255), nullable=False, index=True)
    recipient = Column(String(255), nullable=True, index=True)
    amount = Column(Float, nullable=False)
    currency = Column(String(3), default="USD")
    transaction_type = Column(String(50), default="transfer")  # transfer, payment, request
    status = Column(String(50), default="completed")
    description = Column(Text, nullable=True)
    email_subject = Column(String(500), nullable=True)
    email_date = Column(DateTime, nullable=True)
    source_provider = Column(String(100), nullable=False)  # cashapp, paypal, venmo, etc.
    raw_email_data = Column(Text, nullable=True)  # Store original email content for debugging
    deposited_to = Column(String(255), nullable=True)  # Where money was deposited (e.g., "Cash balance")
    cashapp_transaction_number = Column(String(100), nullable=True)  # Cash App specific transaction ID
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Composite index for better query performance
    __table_args__ = (
        Index('idx_provider_date', 'source_provider', 'created_at'),
        Index('idx_amount_date', 'amount', 'created_at'),
    )
    
    def __repr__(self):
        return f"<Transaction(id={self.id}, amount={self.amount}, sender='{self.sender}')>"
    
    def to_dict(self) -> dict:
        """Convert transaction to dictionary."""
        return {
            "id": self.id,
            "transaction_id": self.transaction_id,
            "sender": self.sender,
            "recipient": self.recipient,
            "amount": self.amount,
            "currency": self.currency,
            "transaction_type": self.transaction_type,
            "status": self.status,
            "description": self.description,
            "email_subject": self.email_subject,
            "email_date": self.email_date.isoformat() if self.email_date else None,
            "source_provider": self.source_provider,
            "raw_email_data": self.raw_email_data,
            "deposited_to": self.deposited_to,
            "cashapp_transaction_number": self.cashapp_transaction_number,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
