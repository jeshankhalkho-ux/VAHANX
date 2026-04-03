import os
import telebot
import requests
from bs4 import BeautifulSoup
import re

# ===============================================
# CONFIG — token read from environment variable
# ===============================================
BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
bot = telebot.TeleBot(BOT_TOKEN)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/138.0.0.0 Mobile Safari/537.36"
    ),
    "Referer": "https://vahanx.in/",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
}

# ===============================================
# SCRAPER
# ===============================================
def get_comprehensive_vehicle_details(rc_number: str) -> dict:
    rc = rc_number.strip().upper()
    url = f"https://vahanx.in/rc-search/{rc}"

    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
    except Exception as e:
        return {"error": f"Failed to fetch data: {str(e)}"}

    def extract_card(label):
        for div in soup.select(".hrcd-cardbody"):
            span = div.find("span")
            if span and label.lower() in span.text.lower():
                p = div.find("p")
                return p.get_text(strip=True) if p else None
        return None

    def extract_from_section(header_text, keys):
        section = soup.find("h3", string=lambda s: s and header_text.lower() in s.lower())
        section_card = section.find_parent("div", class_="hrc-details-card") if section else None
        result = {}
        for key in keys:
            span = section_card.find("span", string=lambda s: s and key in s) if section_card else None
            if span:
                val = span.find_next("p")
                result[key.lower().replace(" ", "_")] = val.get_text(strip=True) if val else None
        return result

    def get_value(label):
        try:
            div = soup.find("span", string=label)
            if div:
                div = div.find_parent("div")
                p = div.find("p") if div else None
                return p.get_text(strip=True) if p else None
        except:
            return None

    try:
        registration_number = soup.find("h1").text.strip()
    except:
        registration_number = rc

    modal_name = extract_card("Modal Name") or get_value("Model Name")
    owner_name = extract_card("Owner Name") or get_value("Owner Name")
    city       = extract_card("City Name") or get_value("City Name")
    phone      = extract_card("Phone") or get_value("Phone")
    address    = extract_card("Address") or get_value("Address")

    ownership = extract_from_section("Ownership Details", [
        "Owner Name", "Father's Name", "Owner Serial No", "Registration Number", "Registered RTO"
    ])
    vehicle = extract_from_section("Vehicle Details", [
        "Model Name", "Maker Model", "Vehicle Class", "Fuel Type",
        "Fuel Norms", "Cubic Capacity", "Seating Capacity"
    ])

    insurance_expired_box = soup.select_one(".insurance-alert-box.expired .title")
    expired_days = None
    if insurance_expired_box:
        match = re.search(r"(\d+)", insurance_expired_box.text)
        expired_days = int(match.group(1)) if match else None

    insurance = extract_from_section("Insurance Information", [
        "Insurance Company", "Insurance No", "Insurance Expiry", "Insurance Upto"
    ])
    insurance_status = "Expired" if expired_days else "Active"

    validity = extract_from_section("Important Dates", [
        "Registration Date", "Vehicle Age", "Fitness Upto", "Insurance Upto",
        "Insurance Expiry In", "Tax Upto", "Tax Paid Upto"
    ])
    puc   = extract_from_section("PUC Details", ["PUC No", "PUC Upto"])
    other = extract_from_section("Other Information", [
        "Financer Name", "Financier Name", "Cubic Capacity", "Seating Capacity",
        "Permit Type", "Blacklist Status", "NOC Details"
    ])

    data = {
        "registration_number": registration_number,
        "status": "success",
        "basic_info": {
            "model_name":   modal_name,
            "owner_name":   owner_name,
            "fathers_name": get_value("Father's Name") or ownership.get("father's_name"),
            "city":         city,
            "phone":        phone,
            "address":      address,
        },
        "ownership_details": {
            "owner_name":   ownership.get("owner_name") or owner_name,
            "fathers_name": ownership.get("father's_name"),
            "serial_no":    ownership.get("owner_serial_no") or get_value("Owner Serial No"),
            "rto":          ownership.get("registered_rto") or get_value("Registered RTO"),
        },
        "vehicle_details": {
            "maker":            vehicle.get("model_name") or modal_name,
            "model":            vehicle.get("maker_model") or get_value("Maker Model"),
            "vehicle_class":    vehicle.get("vehicle_class") or get_value("Vehicle Class"),
            "fuel_type":        vehicle.get("fuel_type") or get_value("Fuel Type"),
            "fuel_norms":       vehicle.get("fuel_norms") or get_value("Fuel Norms"),
            "cubic_capacity":   vehicle.get("cubic_capacity") or other.get("cubic_capacity"),
            "seating_capacity": vehicle.get("seating_capacity") or other.get("seating_capacity"),
        },
        "insurance": {
            "status":           insurance_status,
            "company":          insurance.get("insurance_company") or get_value("Insurance Company"),
            "policy_number":    insurance.get("insurance_no") or get_value("Insurance No"),
            "expiry_date":      insurance.get("insurance_expiry") or get_value("Insurance Expiry"),
            "valid_upto":       insurance.get("insurance_upto") or get_value("Insurance Upto"),
            "expired_days_ago": expired_days,
        },
        "validity": {
            "registration_date": validity.get("registration_date") or get_value("Registration Date"),
            "vehicle_age":       validity.get("vehicle_age") or get_value("Vehicle Age"),
            "fitness_upto":      validity.get("fitness_upto") or get_value("Fitness Upto"),
            "insurance_upto":    validity.get("insurance_upto") or get_value("Insurance Upto"),
            "tax_upto":          validity.get("tax_upto") or validity.get("tax_paid_upto") or get_value("Tax Upto"),
        },
        "puc_details": {
            "puc_number":     puc.get("puc_no") or get_value("PUC No"),
            "puc_valid_upto": puc.get("puc_upto") or get_value("PUC Upto"),
        },
        "other_info": {
            "financer":         other.get("financer_name") or other.get("financier_name") or get_value("Financier Name"),
            "permit_type":      other.get("permit_type") or get_value("Permit Type"),
            "blacklist_status": other.get("blacklist_status") or get_value("Blacklist Status"),
            "noc":              other.get("noc_details") or get_value("NOC Details"),
        },
    }

    def clean_dict(d):
        if isinstance(d, dict):
            return {k: clean_dict(v) for k, v in d.items() if v is not None and v != ""}
        return d

    return clean_dict(data)


# ===============================================
# FORMAT MESSAGE
# ===============================================
def format_vehicle_message(data: dict) -> str:
    if data.get("error"):
        return f"❌ *Error:* {data['error']}"

    lines = []
    lines.append(f"🚗 *RC: {data.get('registration_number', 'N/A')}*")
    lines.append("━━━━━━━━━━━━━━━━━━━━━━")

    bi = data.get("basic_info", {})
    if bi:
        lines.append("📋 *Basic Info*")
        if bi.get("owner_name"):   lines.append(f"  👤 Owner: `{bi['owner_name']}`")
        if bi.get("fathers_name"): lines.append(f"  👨 Father: `{bi['fathers_name']}`")
        if bi.get("model_name"):   lines.append(f"  🚗 Model: `{bi['model_name']}`")
        if bi.get("city"):         lines.append(f"  🏙 City: `{bi['city']}`")
        if bi.get("phone"):        lines.append(f"  📞 Phone: `{bi['phone']}`")
        if bi.get("address"):      lines.append(f"  📍 Address: `{bi['address']}`")

    vd = data.get("vehicle_details", {})
    if vd:
        lines.append("\n🔧 *Vehicle Specs*")
        if vd.get("maker"):            lines.append(f"  🏭 Maker: `{vd['maker']}`")
        if vd.get("model"):            lines.append(f"  📦 Model: `{vd['model']}`")
        if vd.get("vehicle_class"):    lines.append(f"  🏷 Class: `{vd['vehicle_class']}`")
        if vd.get("fuel_type"):        lines.append(f"  ⛽ Fuel: `{vd['fuel_type']}`")
        if vd.get("fuel_norms"):       lines.append(f"  🌱 Norms: `{vd['fuel_norms']}`")
        if vd.get("cubic_capacity"):   lines.append(f"  🔩 CC: `{vd['cubic_capacity']}`")
        if vd.get("seating_capacity"): lines.append(f"  💺 Seats: `{vd['seating_capacity']}`")

    od = data.get("ownership_details", {})
    if od:
        lines.append("\n👥 *Ownership*")
        if od.get("owner_name"):   lines.append(f"  👤 Owner: `{od['owner_name']}`")
        if od.get("fathers_name"): lines.append(f"  👨 Father: `{od['fathers_name']}`")
        if od.get("serial_no"):    lines.append(f"  🔢 Serial: `{od['serial_no']}`")
        if od.get("rto"):          lines.append(f"  🏢 RTO: `{od['rto']}`")

    ins = data.get("insurance", {})
    if ins:
        lines.append("\n🛡 *Insurance*")
        status = ins.get("status", "Unknown")
        icon = "🔴" if status == "Expired" else "🟢"
        lines.append(f"  {icon} Status: `{status}`")
        if ins.get("company"):          lines.append(f"  🏢 Company: `{ins['company']}`")
        if ins.get("policy_number"):    lines.append(f"  📄 Policy: `{ins['policy_number']}`")
        if ins.get("expiry_date"):      lines.append(f"  📅 Expiry: `{ins['expiry_date']}`")
        if ins.get("valid_upto"):       lines.append(f"  ✅ Valid Upto: `{ins['valid_upto']}`")
        if ins.get("expired_days_ago"): lines.append(f"  ⚠️ Expired: `{ins['expired_days_ago']} days ago`")

    val = data.get("validity", {})
    if val:
        lines.append("\n📅 *Validity*")
        if val.get("registration_date"): lines.append(f"  📆 Reg Date: `{val['registration_date']}`")
        if val.get("vehicle_age"):       lines.append(f"  ⏳ Age: `{val['vehicle_age']}`")
        if val.get("fitness_upto"):      lines.append(f"  ✅ Fitness: `{val['fitness_upto']}`")
        if val.get("insurance_upto"):    lines.append(f"  🛡 Insurance: `{val['insurance_upto']}`")
        if val.get("tax_upto"):          lines.append(f"  💵 Tax: `{val['tax_upto']}`")

    puc = data.get("puc_details", {})
    if puc:
        lines.append("\n🔍 *PUC Details*")
        if puc.get("puc_number"):     lines.append(f"  📋 PUC No: `{puc['puc_number']}`")
        if puc.get("puc_valid_upto"): lines.append(f"  📅 Valid: `{puc['puc_valid_upto']}`")

    oi = data.get("other_info", {})
    if oi:
        lines.append("\nℹ️ *Other Info*")
        if oi.get("financer"):    lines.append(f"  🏦 Financer: `{oi['financer']}`")
        if oi.get("permit_type"): lines.append(f"  📜 Permit: `{oi['permit_type']}`")
        if oi.get("blacklist_status"):
            bl = oi["blacklist_status"]
            icon = "🔴" if "yes" in str(bl).lower() else "🟢"
            lines.append(f"  {icon} Blacklist: `{bl}`")
        if oi.get("noc"): lines.append(f"  📄 NOC: `{oi['noc']}`")

    lines.append("\n━━━━━━━━━━━━━━━━━━━━━━")
    lines.append("🔗 _Source: vahanx.in_")
    return "\n".join(lines)


# ===============================================
# BOT HANDLERS
# ===============================================
@bot.message_handler(commands=["start", "help"])
def send_welcome(message):
    text = (
        "👋 *Welcome to Vehicle RC Lookup Bot!*\n\n"
        "Send your RC number directly or use:\n"
        "`/rc DL01AB1234`\n\n"
        "I'll fetch full vehicle details instantly! 🚗"
    )
    bot.reply_to(message, text, parse_mode="Markdown")


@bot.message_handler(commands=["rc"])
def rc_command(message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip():
        bot.reply_to(message, "❌ Please provide an RC number.\nExample: `/rc DL01AB1234`", parse_mode="Markdown")
        return
    lookup(message, parts[1].strip())


@bot.message_handler(func=lambda m: True, content_types=["text"])
def handle_text(message):
    text = message.text.strip()
    if re.match(r'^[A-Za-z]{2}[0-9A-Za-z]{4,10}$', text):
        lookup(message, text)
    else:
        bot.reply_to(
            message,
            "❓ Send a valid RC number like `DL01AB1234` or use `/rc DL01AB1234`",
            parse_mode="Markdown"
        )


def lookup(message, rc_number):
    rc_number = rc_number.upper()
    status_msg = bot.reply_to(message, f"🔍 Looking up *{rc_number}*...", parse_mode="Markdown")
    try:
        data = get_comprehensive_vehicle_details(rc_number)
        reply = format_vehicle_message(data)
        bot.edit_message_text(
            reply,
            chat_id=message.chat.id,
            message_id=status_msg.message_id,
            parse_mode="Markdown"
        )
    except Exception as e:
        bot.edit_message_text(
            f"❌ Error: {str(e)}",
            chat_id=message.chat.id,
            message_id=status_msg.message_id
        )


# ===============================================
# START
# ===============================================
if __name__ == "__main__":
    print("🤖 Bot started...")
    bot.infinity_polling(timeout=10, long_polling_timeout=5)
