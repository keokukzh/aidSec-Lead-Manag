"""Migration script to add research fields to existing database."""
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "leads.db")
DB_PATH = os.path.abspath(DB_PATH)

def migrate():
    """Add research fields to leads table if they don't exist."""
    engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})

    with engine.connect() as conn:
        # Check current columns
        result = conn.execute(text("PRAGMA table_info(leads)"))
        columns = [row[1] for row in result]

        new_columns = [
            ("research_status", "VARCHAR(20)"),
            ("research_last", "DATETIME"),
            ("research_data", "TEXT"),
            ("linkedin", "VARCHAR(500)"),
            ("xing", "VARCHAR(500)"),
        ]

        for col_name, col_type in new_columns:
            if col_name not in columns:
                print(f"Adding column: {col_name}")
                conn.execute(text(f"ALTER TABLE leads ADD COLUMN {col_name} {col_type}"))
                conn.commit()
            else:
                print(f"Column {col_name} already exists")

        # Add indexes if they don't exist
        indexes = [
            ("ix_leads_research_status", "CREATE INDEX IF NOT EXISTS ix_leads_research_status ON leads(research_status)"),
            ("ix_leads_stadt", "CREATE INDEX IF NOT EXISTS ix_leads_stadt ON leads(stadt)"),
        ]

        for idx_name, idx_sql in indexes:
            print(f"Creating index: {idx_name}")
            conn.execute(text(idx_sql))
            conn.commit()

        # Migrate email_history table for Outlook sync
        print("\n--- Migrating email_history table ---")
        result = conn.execute(text("PRAGMA table_info(email_history)"))
        email_columns = [row[1] for row in result]

        email_columns_to_add = [
            ("outlook_message_id", "VARCHAR(100)"),
        ]

        for col_name, col_type in email_columns_to_add:
            if col_name not in email_columns:
                print(f"Adding column: {col_name}")
                conn.execute(text(f"ALTER TABLE email_history ADD COLUMN {col_name} {col_type}"))
                conn.commit()
            else:
                print(f"Column {col_name} already exists")

        print("Migration complete!")

if __name__ == "__main__":
    migrate()
