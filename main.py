from fastapi import FastAPI
from database import Base, engine, SessionLocal
from models import Transaction
from email_parser import fetch_and_store_emails

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Cash App Email Parser API")

@app.get("/transactions")
def get_transactions():
    db = SessionLocal()
    txns = db.query(Transaction).all()
    db.close()
    return [{"id": t.id, "sender": t.sender, "amount": t.amount, "date": t.date} for t in txns]

@app.post("/sync")
def sync_emails():
    new_txns = fetch_and_store_emails()
    return {"new_transactions": new_txns}
