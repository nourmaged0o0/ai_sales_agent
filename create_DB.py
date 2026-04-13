import sqlite3
from datetime import datetime

def setup_database():
    conn = sqlite3.connect('whatsapp_campaign.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS contacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone_number TEXT UNIQUE NOT NULL,
            context_or_interest TEXT,
             status TEXT DEFAULT 'pending'
        )
    ''')
    
    conn.commit()
    conn.close()
    print("Database and table setup completed successfully.")

def add_contact(name, phone_number, context=""):
    conn = sqlite3.connect('whatsapp_campaign.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO contacts (name, phone_number, context_or_interest)
            VALUES (?, ?, ?)
        ''', (name, phone_number, context))
        
        conn.commit()
        print(f"Success: Contact added -> {name} - {phone_number}")
        
    except sqlite3.IntegrityError:
        print(f"Error: The phone number {phone_number} already exists in the database.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    finally:
        conn.close()

def update_contact_status(phone_number, new_status):
    """
    Updates the status and timestamp of a contact.
    Expected statuses: 'contacted', 'failed', 'replied'
    """
    conn = sqlite3.connect('whatsapp_campaign.db')
    cursor = conn.cursor()
    
    try:
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        cursor.execute('''
            UPDATE contacts 
            SET status = ?, last_contacted_at = ?
            WHERE phone_number = ?
        ''', (new_status, current_time, phone_number))
        
        if cursor.rowcount > 0:
            conn.commit()
            print(f"Success: Status for {phone_number} updated to '{new_status}'.")
            return True
        else:
            print(f"Warning: Phone number {phone_number} not found.")
            return False
            
    except Exception as e:
        print(f"Error updating status: {e}")
        return False
    finally:
        conn.close()

# ==========================================
# Testing Area
# ==========================================
if __name__ == "__main__":
    # Step 1: Initialize the database
    setup_database()
    
    print("\n--- Populating Database ---")
    # Step 2: Add test contacts with specific contexts for the AI to read
    add_contact("Nour Maged", "+201270187283", "Interested in digital marketing for restaurants")
    add_contact("Mohamed Walid", "+201097401832", "Attended the AI webinar last week")
    add_contact("omar ahmed", "+201034238921", "Potential lead, showed interest in our services during the last campaign")
    add_contact("Fatma Gad", "+201015895059", "Old client, needs to be informed about the new update")
    add_contact("Aly Elbadry", "+201286964627", "New client, needs to be informed about the new company")
    
    
    # Attempting to add a duplicate to test error handling

    print("\n--- Testing the Update Function ---")
    # Step 3: Simulate the LangChain Agent updating a status after sending a message
