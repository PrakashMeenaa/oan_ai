import asyncio
import html
import logging
from fastapi import APIRouter, Request
from pydantic import BaseModel, EmailStr, Field
import resend
from app.core.supabase import get_supabase
from app.core.config import get_settings, Settings
from app.core.limiter import limiter

router = APIRouter(prefix="/api", tags=["enquiry"])
logger = logging.getLogger("oan_ai_service.enquiry")


class ChatHistoryMessage(BaseModel):
    role: str
    content: str


class EnquiryRequest(BaseModel):
    name: str = Field(default="", max_length=200)
    email: EmailStr
    message: str = Field(min_length=1, max_length=4000)
    chat_history: list[ChatHistoryMessage] = Field(default_factory=list)


class EnquiryResponse(BaseModel):
    success: bool
    message: str


def build_email_html(body: EnquiryRequest) -> str:
    safe_name = html.escape(body.name or "Not provided")
    safe_email = html.escape(str(body.email))
    safe_message = html.escape(body.message)

    transcript_rows = ""
    for msg in body.chat_history:
        role_label = "Buyer" if msg.role == "user" else "Aria (AI)"
        bg = "#f0f4ff" if msg.role == "user" else "#f9fafb"
        align = "right" if msg.role == "user" else "left"
        safe_content = html.escape(msg.content).replace(chr(10), "<br/>")
        transcript_rows += f"""
        <tr>
          <td style="padding:8px 12px;background:{bg};border-radius:8px;
                     text-align:{align};margin-bottom:6px;display:block">
            <span style="font-size:11px;font-weight:600;color:#6b7280;
                         text-transform:uppercase;letter-spacing:0.5px">
              {role_label}
            </span><br/>
            <span style="font-size:14px;color:#111827;line-height:1.5">
              {safe_content}
            </span>
          </td>
        </tr>
        <tr><td style="height:6px"></td></tr>
        """

    transcript_section = f"""
    <h2 style="font-size:16px;color:#374151;margin:28px 0 12px">
      Chat Transcript
    </h2>
    <table width="100%" cellpadding="0" cellspacing="0">
      {transcript_rows}
    </table>
    """ if transcript_rows else ""

    return f"""
    <!DOCTYPE html>
    <html>
    <body style="font-family:Arial,sans-serif;background:#f3f4f6;
                 padding:24px;margin:0">
      <div style="max-width:600px;margin:0 auto;background:white;
                  border-radius:12px;overflow:hidden;
                  box-shadow:0 1px 3px rgba(0,0,0,0.1)">

        <div style="background:#1d4ed8;padding:24px 28px">
          <h1 style="color:white;margin:0;font-size:20px">
            New Business Enquiry — OAN Group
          </h1>
          <p style="color:#bfdbfe;margin:4px 0 0;font-size:13px">
            Received via OAN AI Sales Consultant (Aria)
          </p>
        </div>

        <div style="padding:24px 28px">
          <table width="100%" cellpadding="0" cellspacing="0">
            <tr>
              <td style="padding:10px 0;border-bottom:1px solid #e5e7eb">
                <span style="font-size:12px;color:#6b7280;font-weight:600;
                             text-transform:uppercase">Name</span><br/>
                <span style="font-size:15px;color:#111827">
                  {safe_name}
                </span>
              </td>
            </tr>
            <tr>
              <td style="padding:10px 0;border-bottom:1px solid #e5e7eb">
                <span style="font-size:12px;color:#6b7280;font-weight:600;
                             text-transform:uppercase">Email</span><br/>
                <a href="mailto:{safe_email}"
                   style="font-size:15px;color:#1d4ed8">
                  {safe_email}
                </a>
              </td>
            </tr>
            <tr>
              <td style="padding:10px 0">
                <span style="font-size:12px;color:#6b7280;font-weight:600;
                             text-transform:uppercase">Requirement</span><br/>
                <span style="font-size:15px;color:#111827;line-height:1.6">
                  {safe_message}
                </span>
              </td>
            </tr>
          </table>

          {transcript_section}

          <div style="margin-top:28px;padding:16px;background:#f0fdf4;
                      border-radius:8px;border-left:4px solid #16a34a">
            <p style="margin:0;font-size:13px;color:#15803d">
              <strong>Action required:</strong> Reply directly to
              <a href="mailto:{safe_email}" style="color:#15803d">
                {safe_email}
              </a>
              to follow up with this buyer.
            </p>
          </div>
        </div>

        <div style="padding:16px 28px;background:#f9fafb;
                    border-top:1px solid #e5e7eb">
          <p style="margin:0;font-size:12px;color:#9ca3af">
            OAN Group · info@oangroup.in · +91-141-4035484 ·
            oangroup.in
          </p>
        </div>
      </div>
    </body>
    </html>
    """


def save_and_notify(body: EnquiryRequest, settings: Settings) -> None:
    supabase = get_supabase()

    supabase.table("oan_enquiries").insert({
        "name": body.name,
        "email": str(body.email),
        "message": body.message,
    }).execute()

    if not settings.oan_sales_email:
        logger.warning("OAN_SALES_EMAIL not set, enquiry saved without sending email")
        return

    resend.api_key = settings.resend_api_key

    resend.Emails.send({
        "from": "Aria — OAN AI <onboarding@resend.dev>",
        "to": [settings.oan_sales_email],
        "reply_to": str(body.email),
        "subject": f"New Enquiry from {body.name or body.email} — OAN AI",
        "html": build_email_html(body),
    })


@router.post("/enquiry", response_model=EnquiryResponse)
@limiter.limit("2/minute;5/day")
async def submit_enquiry(body: EnquiryRequest, request: Request) -> EnquiryResponse:
    settings = get_settings()

    try:
        await asyncio.to_thread(save_and_notify, body, settings)
    except Exception:
        logger.exception("enquiry submission failed")
        return EnquiryResponse(success=False, message="Something went wrong saving your enquiry. Please try again.")

    logger.info(f"enquiry saved, email_domain={str(body.email).split('@')[-1]}")
    return EnquiryResponse(success=True, message="Enquiry received")