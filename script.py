import os
import sqlite3
import requests
from dotenv import load_dotenv
from langchain.tools import tool
from langchain_groq import ChatGroq
from langchain.agents import create_agent

load_dotenv()



#tools

@tool
def get_pending_leads() -> list:
    """Fetches a list of leads from the database who have a 'pending' status."""
    conn = sqlite3.connect('whatsapp_campaign.db')
    cursor = conn.cursor()
    cursor.execute("SELECT name, phone_number, context_or_interest FROM contacts WHERE status = 'pending'")
    leads = cursor.fetchall()
    conn.close()
    return [{"name": row[0], "phone": row[1], "interest": row[2]} for row in leads]

@tool
def send_whatsapp_message(phone: str, message_in_arabic: str) -> bool:
    """
    Sends a real WhatsApp text message to the given phone number using Meta API.
    Returns True if the message was delivered, False otherwise.
    """
    print(f"\n [Tool Execution] Sending real WhatsApp message to {phone}...")
    print(f" AI Generated Message:\n{message_in_arabic}")
    
    PHONE_NUMBER_ID = os.getenv("META_PHONE_NUMBER_ID")
    ACCESS_TOKEN = os.getenv("META_ACCESS_TOKEN")
    url = f"https://graph.facebook.com/v25.0/{PHONE_NUMBER_ID}/messages"
    
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    
    formatted_phone = phone.replace("+", "")
    
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": formatted_phone,
        "type": "text", 
        "text": {
            "preview_url": False,
            "body": message_in_arabic
        }
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        response_data = response.json()
        if response.status_code in [200, 201]:
            print("[Status] Reached & Sent Successfully!")
            return True
        else:
            print(f" [Status] Couldn't Reach. Meta Error: {response_data}")
            return False
    except Exception as e:
        print(f"[Error] Request failed: {e}")
        return False

@tool
def update_lead_status(phone: str, status: str):
    """
    Updates the status of the lead in the database. 
    The status MUST be either 'reached' or 'couldn't reach'.
    """
    conn = sqlite3.connect('whatsapp_campaign.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE contacts SET status = ? WHERE phone_number = ?", (status, phone))
    conn.commit()
    conn.close()
    print(f"🔄 [Database] Updated {phone} to '{status}'.")
    return f"Success: {phone} updated to {status}"


tools = [get_pending_leads, send_whatsapp_message, update_lead_status]
llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0.7)
system_prompt = """
أنت موظف مبيعات مصري ذكي واحترافي.
مهمتك الأساسية والوحيدة هي التواصل مع العملاء عبر الواتساب **باللهجة المصرية الطبيعية جداً**.
ممنوع منعاً باتاً إرسال أي حرف باللغة الإنجليزية للعميل.

قاعدة البيانات قد تحتوي على اهتمامات العميل (interest) باللغة الإنجليزية. يجب عليك قراءتها، فهمها، ثم صياغة رسالة مصرية ودية بناءً عليها.

اتبع هذه الخطوات بدقة:
1. استخدم أداة `get_pending_leads` لجلب بيانات العملاء الذين لم يتم التواصل معهم.
2. لكل عميل، قم بالآتي:
   - قم بتأليف رسالة واتساب قصيرة وودية باللهجة المصرية (مثال: "أهلاً بك يا أستاذ/ة [الاسم]، إحنا عرفنا إنك مهتم بـ [الاهتمام بالمصري]، وحابين نساعدك...").
   - استخدم أداة `send_whatsapp_message` لإرسال هذه الرسالة. (تأكد أن المدخل message_in_arabic عربي 100%).
   - بناءً على نتيجة الإرسال، استخدم فوراً أداة `update_lead_status` لتحديث حالته إلى "reached" أو "couldn't reach".
3. كرر العملية حتى تنتهي من كل العملاء.
"""
agent = create_agent(
    model=llm,
    tools=tools,
    system_prompt=system_prompt
)


if __name__ == "__main__":
    print("Starting WhatsApp Automation Agent...\n")
    
    agent.invoke({
        "messages": [
            {"role": "user", "content": "Start the WhatsApp outreach campaign for all pending leads in the database."}
        ]
    })