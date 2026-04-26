import os
import sqlite3
import requests
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()

def get_pending_leads():
    conn = sqlite3.connect('whatsapp_campaign.db')
    cursor = conn.cursor()
    cursor.execute("SELECT name, phone_number, context_or_interest FROM contacts WHERE status = 'pending'")
    leads = cursor.fetchall()
    conn.close()
    return [{"name": row[0], "phone": row[1], "interest": row[2]} for row in leads]

def check_interest_cache(interest):
    conn = sqlite3.connect('whatsapp_campaign.db')
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS message_cache (interest TEXT PRIMARY KEY, template TEXT)")
    cursor.execute("SELECT template FROM message_cache WHERE interest = ?", (interest,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

def save_interest_cache(interest, template):
    conn = sqlite3.connect('whatsapp_campaign.db')
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS message_cache (interest TEXT PRIMARY KEY, template TEXT)")
    cursor.execute("INSERT OR REPLACE INTO message_cache (interest, template) VALUES (?, ?)", (interest, template))
    conn.commit()
    conn.close()

def send_whatsapp_message(phone, message_in_arabic):
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
        return response.status_code in [200, 201]
    except:
        return False

def update_lead_status(phone, status):
    conn = sqlite3.connect('whatsapp_campaign.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE contacts SET status = ? WHERE phone_number = ?", (status, phone))
    conn.commit()
    conn.close()

if __name__ == "__main__":
    llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0.4)
    # llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.4)
#     llm = ChatOpenAI(
#     # openai_api_key=os.getenv("openai_api_key"),
#     openai_api_base="https://openrouter.ai/api/v1", 
#     model="inclusionai/ling-2.6-1t:free", 
#     temperature=0.3,
# )
    # llm = ChatOpenAI(
    #     api_key=os.getenv("SILICONFLOW_API_KEY"), 
    #     base_url="https://api.siliconflow.com/v1", 
    #     model="Qwen/Qwen3-VL-32B-Instruct",       
    #     temperature=0.3,
    # )

    # llm = ChatOpenAI(
    #     api_key=os.getenv("SILICONFLOW_API_KEY"), 
    #     base_url="https://api.siliconflow.com/v1", 
    #     model="deepseek-ai/DeepSeek-V4-Pro",      
    #     temperature=0.3,
    # )
    leads = get_pending_leads()

    for lead in leads:
        name = lead["name"]
        phone = lead["phone"]
        interest = lead["interest"]

        template = check_interest_cache(interest)

        if template:
            print(f"Cache HIT: Skipping LLM for '{interest}'")
            final_message = template.replace("[NAME]", name)
        else:
            print(f"Cache MISS: Calling LLM for '{interest}'")
            prompt = f"""أنت بائع مصري محترف تكتب رسالة واتساب لعميل مهتم بـ '{interest}'.
            اكتب رسالة واحدة فقط (سطرين كحد أقصى) والتزم بهذه الشروط الإجبارية حرفياً:
            1.  - قم بتأليف رسالة واتساب قصيرة وودية باللهجة المصرية (مثال: "أهلاً بيك يا أستاذ/ة [الاسم]، إحنا عرفنا إنك مهتم بـ [الاهتمام بالمصري]، وحابين نساعدك...").
            2. ابدأ الرسالة بـ "اهلا يا [NAME]" (اكتب كلمة اهلا بدون همزات، واكتب [NAME] كما هي بالأقواس المربعة).
            3. ممنوع منعاً باتاً استخدام كلمات فصحى مثل "مرحبا" أو "كيف حالك". استخدم لهجة شات مصرية دارجة وطبيعية 100%.
            4. ممنوع منعاً باتاً وضع فواصل (،) أو نقاط (.) في وسط الجمل أو في نهاية السطور.
            5. ممنوع كتابة أي كلمة باللغة الإنجليزية باستثناء [NAME] فقط.
            6. أخرج نص الرسالة فقط لا غير، بدون أي مقدمات أو خيارات أو شروحات."""
            
            response = llm.invoke(prompt)
            template = response.content.strip()
            usage = response.usage_metadata
            if usage:
                print(f"📊 [Tokens Billed] Prompt: {usage['input_tokens']} | Generated: {usage['output_tokens']} | Total: {usage['total_tokens']}")
            save_interest_cache(interest, template)
            final_message = template.replace("[NAME]", name)

        success = send_whatsapp_message(phone, final_message)
        status = "reached" if success else "couldn't reach"
        update_lead_status(phone, status)
        
