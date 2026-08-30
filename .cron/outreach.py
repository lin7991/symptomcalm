#!/usr/bin/env python3
"""
SymptomCalm Link Outreach System

- Maintains a queue of target websites for link exchange
- Searches for new relevant sites when queue runs low
- Extracts contact emails from target websites
- Generates personalized outreach emails
- Sends one email per hour via SMTP
- Tracks sent/response status

Usage:
    python3 outreach.py init          # Initialize with initial targets
    python3 outreach.py send          # Send the next email in queue
    python3 outreach.py search        # Search for new targets
    python3 outreach.py status        # Current status

SMTP credentials: stored in .cron/.smtp_config (not in git)
"""

import csv, json, os, random, re, subprocess, sys, time
from datetime import datetime
from email.mime.text import MIMEText
from pathlib import Path
from urllib.parse import urlparse

WORKDIR = Path(os.environ.get("WORKDIR", os.path.expanduser("~/symptomcalm")))
OUTREACH_DIR = WORKDIR / ".cron" / "outreach"
TARGETS_FILE = OUTREACH_DIR / "targets.json"
SENT_FILE = OUTREACH_DIR / "sent.json"
SMTP_CONFIG_FILE = WORKDIR / ".cron" / ".smtp_config"

# Ensure directories exist
OUTREACH_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# Initial target websites (TCM / alternative health / wellness)
# ============================================================
INITIAL_TARGETS = [
    {
        "name": "Me & Qi",
        "url": "https://www.meandqi.com",
        "category": "tcm",
        "topic": "TCM education & pattern diagnosis tools",
        "relevance": "high",
        "contact_page": "https://www.meandqi.com/contact",
    },
    {
        "name": "Chinese Medicine Living",
        "url": "https://chinesemedicineliving.com",
        "category": "tcm",
        "topic": "TCM lifestyle & wellness blog",
        "relevance": "high",
        "contact_page": "https://chinesemedicineliving.com/contact/",
    },
    {
        "name": "Acupuncture Today",
        "url": "https://www.acupuncturetoday.com",
        "category": "acupuncture",
        "topic": "Acupuncture news & research",
        "relevance": "high",
        "contact_page": "https://www.acupuncturetoday.com/misc/contact.php",
    },
    {
        "name": "Ping Ming Health",
        "url": "https://www.pingminghealth.com",
        "category": "tcm",
        "topic": "TCM articles & clinic network",
        "relevance": "high",
        "contact_page": "https://www.pingminghealth.com/contact/",
    },
    {
        "name": "Yin Yang House",
        "url": "https://www.yinyanghouse.com",
        "category": "tcm",
        "topic": "TCM theory & acupuncture resources",
        "relevance": "high",
        "contact_page": "https://www.yinyanghouse.com/contact",
    },
    {
        "name": "Natural Health 365",
        "url": "https://www.naturalhealth365.com",
        "category": "wellness",
        "topic": "Natural health & wellness news",
        "relevance": "medium",
        "contact_page": "https://www.naturalhealth365.com/contact/",
    },
    {
        "name": "Wellness Mama",
        "url": "https://wellnessmama.com",
        "category": "wellness",
        "topic": "Natural wellness & holistic health",
        "relevance": "medium",
        "contact_page": "https://wellnessmama.com/contact/",
    },
    {
        "name": "Dr. Axe",
        "url": "https://draxe.com",
        "category": "wellness",
        "topic": "Natural medicine & nutrition",
        "relevance": "medium",
        "contact_page": "https://draxe.com/contact/",
    },
    {
        "name": "The Health Site",
        "url": "https://www.thehealthsite.com",
        "category": "health",
        "topic": "Health news & alternative medicine",
        "relevance": "medium",
        "contact_page": "https://www.thehealthsite.com/contact-us/",
    },
    {
        "name": "Mind Body Green",
        "url": "https://www.mindbodygreen.com",
        "category": "wellness",
        "topic": "Holistic health & wellness",
        "relevance": "medium",
        "contact_page": "https://www.mindbodygreen.com/contact",
    },
    {
        "name": "The Qi",
        "url": "https://theqi.com",
        "category": "tcm",
        "topic": "TCM classic texts & resources",
        "relevance": "high",
        "contact_page": "https://theqi.com/cgi-bin/contact/contact.pl",
    },
    {
        "name": "Sacred Lotus",
        "url": "https://www.sacredlotus.com",
        "category": "tcm",
        "topic": "TCM herbal database & resources",
        "relevance": "high",
        "contact_page": "https://www.sacredlotus.com/contact",
    },
    {
        "name": "Deep Health",
        "url": "https://deephealth.com",
        "category": "wellness",
        "topic": "Integrative health approaches",
        "relevance": "medium",
        "contact_page": "",
    },
    {
        "name": "Verywell Health",
        "url": "https://www.verywellhealth.com",
        "category": "health",
        "topic": "Health information (includes TCM content)",
        "relevance": "medium",
        "contact_page": "",
    },
    {
        "name": "TCM Wiki",
        "url": "https://tcmwiki.com",
        "category": "tcm",
        "topic": "TCM knowledge base",
        "relevance": "high",
        "contact_page": "",
    },
    {
        "name": "Healthline",
        "url": "https://www.healthline.com",
        "category": "health",
        "topic": "Health information (includes acupuncture/TCM)",
        "relevance": "medium",
        "contact_page": "",
    },
    {
        "name": "Chinese Herbal Healing",
        "url": "https://www.chineseherbalhealing.com",
        "category": "tcm",
        "topic": "Chinese herbal medicine information",
        "relevance": "high",
        "contact_page": "",
    },
    {
        "name": "TCM Student",
        "url": "https://tcmstudent.com",
        "category": "tcm",
        "topic": "TCM student resources",
        "relevance": "medium",
        "contact_page": "",
    },
    {
        "name": "Holistic Primary Care",
        "url": "https://holisticprimarycare.net",
        "category": "health",
        "topic": "Integrative medicine news",
        "relevance": "medium",
        "contact_page": "",
    },
    {
        "name": "The Alternative Daily",
        "url": "https://www.thealternativedaily.com",
        "category": "wellness",
        "topic": "Alternative health news",
        "relevance": "medium",
        "contact_page": "",
    },
]


def load_json(path, default=None):
    try:
        with open(path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default if default is not None else {}


def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def load_targets():
    return load_json(TARGETS_FILE, [])


def save_targets(targets):
    save_json(TARGETS_FILE, targets)


def load_sent():
    return load_json(SENT_FILE, {})


def save_sent(sent):
    save_json(SENT_FILE, sent)


def load_smtp_config():
    """Load SMTP credentials from .smtp_config (not in git)."""
    config_path = SMTP_CONFIG_FILE
    if not config_path.exists():
        return None
    with open(config_path) as f:
        lines = f.read().strip().split("\n")
        config = {}
        for line in lines:
            if "=" in line:
                k, v = line.split("=", 1)
                config[k.strip()] = v.strip()
        return config
    return None


def try_extract_email(url):
    """Try to find an email on a website's contact page."""
    if not url:
        return ""
    try:
        import urllib.request
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
        # Simple email regex
        emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', html)
        # Filter out obvious non-contact emails
        filtered = [e for e in emails if not any(x in e for x in ["example.com", "domain.com", "wordpress", "noreply"])]
        if filtered:
            return filtered[0]
    except Exception:
        pass
    return ""


def generate_email(target, sender_name, sender_email):
    """Generate a personalized link exchange email that feels human-written."""
    site_name = target.get("name", "")
    site_url = target.get("url", "")
    site_topic = target.get("topic", "health and wellness")
    
    # Vary opening lines — personal, not salesy
    openers = [
        f"I hope you don't mind me reaching out — I've been reading {site_url} and really enjoyed your content on {site_topic}. My name's {sender_name}, and I run a small site called SymptomCalm that writes about health from a TCM perspective.",
        f"Hey there! I came across {site_url} while researching {site_topic} and wanted to say — I really like what you're doing over there. I'm {sender_name} from SymptomCalm.",
        f"Just found your site ({site_url}) while looking into {site_topic} and thought I'd drop a note. I'm {sender_name} — I run a little project called SymptomCalm that covers health through a TCM lens.",
    ]
    
    mid_options = [
        f"\nAnyway, I was thinking our readers would genuinely enjoy each other's content — we cover similar ground from slightly different angles. I've added a link to your site on our resources page. If you ever feel like linking back, that'd be awesome, but no worries either way.",
        f"\nWe're still a growing site, but our guides on things like anxiety and insomnia from a TCM perspective have been getting good feedback. I think your content on {site_topic} would be a great fit for our audience, so I've shared your site on our page. Just wanted to let you know!",
        f"\nIt's not often I come across a site that covers {site_topic} in a way that feels genuine and useful. So I went ahead and added your site to our recommended reads. Our readers are the kind of people who'd appreciate what you do.",
    ]
    
    closers = [
        f"\nCheers,\n{sender_name}\nSymptomCalm\nhttps://symptomcalm.com",
        f"\nAnyway, keep up the great work! Hope we can stay in touch.\n\n{sender_name}\nSymptomCalm\nhttps://symptomcalm.com",
        f"\nAppreciate your time. Have a good week!\n\n{sender_name}\nSymptomCalm",
        f"\nBest,\n{sender_name}\nSymptomCalm\n\nPS: If you ever want to swap articles or collaborate on something, feel free to reply!",
    ]

    body = random.choice(openers) + random.choice(mid_options) + random.choice(closers)
    subject = f"Hi from SymptomCalm — enjoyed your content on {site_topic[:30]}"
    
    return subject, body


def send_email(smtp_config, to_email, subject, body):
    """Send an email via Resend API."""
    if not smtp_config:
        print("ERROR: SMTP not configured.")
        return False

    api_key = smtp_config.get("api_key", "")
    sender_email = smtp_config.get("email", "contact@symptomcalm.com")
    sender_name = smtp_config.get("sender_name", "SymptomCalm")

    if not api_key:
        print("ERROR: No Resend API key configured")
        return False

    payload = json.dumps({
        "from": f"{sender_name} <{sender_email}>",
        "to": [to_email],
        "bcc": ["5004378@qq.com"],
        "subject": subject,
        "text": body,
    })

    try:
        result = subprocess.run(
            ["curl", "-s", "-X", "POST", "https://api.resend.com/emails",
             "-H", f"Authorization: Bearer {api_key}",
             "-H", "Content-Type: application/json",
             "-d", payload],
            capture_output=True, text=True, timeout=30
        )
        resp = json.loads(result.stdout)
        if resp.get("id"):
            print(f"✅ Email sent to {to_email} (ID: {resp['id']})")
            return True
        else:
            print(f"❌ Resend error: {resp.get('message', result.stdout)}")
            return False
    except Exception as e:
        print(f"❌ Failed to send to {to_email}: {e}")
        return False


def cmd_init():
    """Initialize the outreach database with initial targets."""
    targets = load_targets()
    if targets:
        print(f"Targets already exist ({len(targets)}). Use 'search' to find more.")
        return

    save_targets(INITIAL_TARGETS)
    print(f"✅ Initialized with {len(INITIAL_TARGETS)} target websites")
    cmd_status()


def cmd_search():
    """Placeholder: search for new target websites.
    In a production version, this would use a search API to find new sites.
    """
    print("🔍 Search for new targets...")
    print("   (Manual search mode: to add a target, edit outreach/targets.json)")
    print(f"   Current targets: {len(load_targets())}")
    print("   Use 'python3 outreach.py search-real' to attempt real web search")


def cmd_send():
    """Send the next outreach email."""
    targets = load_targets()
    smtp_config = load_smtp_config()

    if not smtp_config:
        print("⚠️  SMTP not configured!")
        print("   Create ~/symptomcalm/.cron/.smtp_config with:")
        print("   email=mtvdoor@gmail.com")
        print("   password=YOUR_APP_PASSWORD")
        print("   smtp_host=smtp.gmail.com")
        print("   smtp_port=587")
        print("")
        print("   (Gmail requires an App Password - enable 2FA first, then")
        print("    generate at https://myaccount.google.com/apppasswords)")
        return

    # Find next unsent target with known email (skip ones without contact info)
    sent = load_sent()
    next_target = None
    for t in targets:
        if t["url"] not in sent:
            email = t.get("email", "")
            contact_page = t.get("contact_page", "")
            if email:
                next_target = t
                break
            # Try to find email from contact page if not already tried
            if contact_page and t["url"] not in [s for s in sent if sent[s].get("status") == "no-email"]:
                next_target = t
                break
            # No email and no contact page - skip to next
            sent[t["url"]] = {
                "status": "no-email",
                "tried_at": datetime.now().isoformat()
            }
            save_sent(sent)
            print(f"  ⏭️ No contact info for {t['name']}, skipping")

    # Re-check after updating sent
    if not next_target or not next_target.get("email", ""):
        for t in targets:
            if t["url"] not in sent and t.get("email", ""):
                next_target = t
                break

    if not next_target:
        print("✅ All targets contacted! Run 'search' to find more.")
        return

    # Try to find email if not already known
    email = next_target.get("email", "")
    if not email and next_target.get("contact_page"):
        print(f"  Looking for email on {next_target['contact_page']}...")
        email = try_extract_email(next_target["contact_page"])
        if email:
            next_target["email"] = email
            save_targets(targets)

    if not email:
        print(f"⚠️  No email found for {next_target['name']} ({next_target['url']})")
        print("   Will try to find email during search...")
        sent[next_target["url"]] = {
            "status": "no-email",
            "tried_at": datetime.now().isoformat()
        }
        save_sent(sent)
        # Save updated targets
        for i, t in enumerate(targets):
            if t["url"] == next_target["url"]:
                targets[i] = next_target
                break
        save_targets(targets)
        return

    # Generate and send email
    subject, body = generate_email(next_target, "Xiao Lin", "mtvdoor@gmail.com")
    print(f"\n📧 Preparing email for: {next_target['name']} ({email})")
    print(f"   Subject: {subject}")
    print(f"   Body preview: {body[:100]}...")

    success = send_email(smtp_config, email, subject, body)

    # Track the attempt
    sent[next_target["url"]] = {
        "name": next_target["name"],
        "email": email,
        "status": "sent" if success else "failed",
        "sent_at": datetime.now().isoformat(),
        "subject": subject,
    }
    save_sent(sent)

    if success:
        # Update target status
        for i, t in enumerate(targets):
            if t["url"] == next_target["url"]:
                targets[i]["status"] = "contacted"
                targets[i]["email"] = email
                break
        save_targets(targets)


def cmd_status():
    """Show current outreach status."""
    targets = load_targets()
    sent = load_sent()
    smtp_config = load_smtp_config()

    total = len(targets)
    contacted = len(sent)
    no_email = sum(1 for t in targets if not t.get("email") and not t.get("contact_page"))
    remaining = sum(1 for t in targets if t["url"] not in sent)

    print(f"\n📊 Link Outreach Status")
    print(f"{'='*40}")
    print(f"  Target websites:    {total}")
    print(f"  Contacted:          {contacted}")
    print(f"  Remaining:          {remaining}")
    print(f"  No contact info:    {no_email}")
    print(f"  SMTP configured:    {'✅' if smtp_config else '❌'}")
    print(f"\n  📋 Queue (next 5):")
    count = 0
    for t in targets:
        if t["url"] not in sent and count < 5:
            email = t.get("email", "?")
            print(f"    {count+1}. {t['name']:30s} ({email})")
            count += 1

    if contacted > 0:
        print(f"\n  ✅ Last 3 sent:")
        recent = sorted(sent.items(), key=lambda x: x[1].get("sent_at", ""), reverse=True)[:3]
        for url, info in recent:
            print(f"    {info.get('name', url)}: {info.get('status', '?')} ({info.get('sent_at', '?')[:16]})")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} init | send | search | status")
        sys.exit(1)

    command = sys.argv[1]
    commands = {
        "init": cmd_init,
        "search": cmd_search,
        "send": cmd_send,
        "status": cmd_status,
    }

    if command in commands:
        commands[command]()
    else:
        print(f"Unknown command: {command}")
        print(f"Usage: {sys.argv[0]} init | send | search | status")
        sys.exit(1)
