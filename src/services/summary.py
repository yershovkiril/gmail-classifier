import datetime
import logging

import markdown
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate

from src.config import settings
from src.services.gmail import GmailClient
from src.services.llm_factory import get_llm

logger = logging.getLogger(__name__)

def generate_daily_summary() -> None:
    """
    Fetches all emails from the last N hours, generates an LLM digest,
    and sends it to the user.
    """
    logger.info(f"Starting Daily Summary generation task for last {settings.summary_frequency_hours} hours...")

    try:
        gmail_client = GmailClient()
    except Exception as e:
        logger.critical(f"Failed to initialize Gmail Client for summary: {e}")
        return

    # Fetch emails from the configured frequency period
    emails = gmail_client.get_recent_emails(hours=settings.summary_frequency_hours)
    if not emails:
        logger.info(f"No emails received in the last {settings.summary_frequency_hours} hours. Skipping summary.")
        return

    logger.info(f"Fetched {len(emails)} emails. Building prompt...")

    # Compact emails representation to fit context window safely
    email_lines = []
    for email in emails:
        sender = email.get("sender", "Unknown")
        subject = email.get("subject", "No Subject")
        snippet = email.get("snippet", "")
        email_lines.append(f"- From: {sender} | Subj: {subject} | Snippet: {snippet}")

    emails_content = "\n".join(email_lines)
    allowed_categories = "\n".join(f"- {k}: {v}" for k, v in settings.categories.items())

    prompt = PromptTemplate.from_template(
        """You are a highly efficient executive assistant. Attached is a raw list of ALL emails I received in the last {summary_frequency_hours} hours.

Your task is to organize this chaos into a highly readable, concise Daily Digest.

### MY CATEGORIES:
{categories_text}

### INSTRUCTIONS:
1. Group the emails by the categories listed above. (If some don't fit, use an 'Other / Uncategorized' section).
2. **CRITICAL:** If a category has ZERO emails, DO NOT include its heading in the output at all. Omit empty categories entirely.
3. Within each category, synthesize the emails into bullet points. DO NOT just list every single email. Combine related emails (e.g., "3 marketing emails from Amazon").
4. Highlight Action Items: If an email sounds like I need to reply, pay a bill, or take action, highlight it with a priority flag like 🔴.
5. Formatting: Output your response in valid Markdown. Use `### ` (H3) for category names, and standard `- ` bullets for the emails. Do not use H1 or H2 headings.

### RAW EMAILS (LAST {summary_frequency_hours}h):
{emails_content}

Write the Digest now:"""
    )

    try:
        llm = get_llm()
        chain = prompt | llm | StrOutputParser()
        digest_markdown = chain.invoke({
            "categories_text": allowed_categories,
            "emails_content": emails_content,
            "summary_frequency_hours": settings.summary_frequency_hours
        })

        # Convert Markdown to basic HTML for the email
        html_content = markdown.markdown(digest_markdown)

        html_body = f"""
        <html>
            <head>
                <style>
                    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; line-height: 1.6; color: #333; max-width: 800px; margin: 0 auto; padding: 20px; }}
                    h2 {{ color: #2c3e50; border-bottom: 2px solid #eee; padding-bottom: 10px; margin-top: 5px; }}
                    h3 {{ color: #34495e; margin-top: 25px; border-bottom: 1px solid #f0f0f0; padding-bottom: 5px; }}
                    ul {{ padding-left: 20px; }}
                    li {{ margin-bottom: 8px; }}
                    .digest-content {{ background: #ffffff; padding: 30px; border-radius: 8px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); }}
                    .header {{ text-align: center; margin-bottom: 30px; }}
                    .date-sub {{ color: #7f8c8d; font-size: 0.9em; margin-top: -10px; }}
                    strong {{ color: #2c3e50; }}
                </style>
            </head>
            <body style="background-color: #f7f9fc; padding: 20px;">
                <div class="digest-content">
                    <div class="header">
                        <h2>\U0001F4EC Daily Agent Digest</h2>
                        <p class="date-sub">{datetime.date.today().strftime('%B %d, %Y')}</p>
                    </div>
                    <div>{html_content}</div>
                </div>
            </body>
        </html>
        """

        logger.info("Digest generated successfully. Sending email...")
        subject = f"Your Daily Inbox Summary - {datetime.date.today().strftime('%b %d')}"
        gmail_client.send_email(subject, html_body)

    except Exception as e:
        logger.error(f"Failed to generate or send the Daily Summary: {e}")
