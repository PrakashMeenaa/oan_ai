from fastapi import APIRouter
from pydantic import BaseModel, Field
import resend
from app.core.supabase import get_supabase
from app.core.config import get_settings

router = APIRouter(prefix="/api", tags=["enquiry"])


class ChatHistoryMessage(BaseModel):
    role: str
    content: str


class EnquiryRequest(BaseModel):
    name: str = Field(default="")
    email: str = Field(min_length=5)
    message: str = Field(min_length=1)
    chat_history: list[ChatHistoryMessage] = Field(default_factory=list)


class EnquiryResponse(BaseModel):
    success: bool
    message: str


def build_email_html(body: EnquiryRequest) -> str:
    transcript_rows = ""
    for msg in body.chat_history:
        role_label = "Buyer" if msg.role == "user" else "Aria (AI)"
        bg = "#f0f4ff" if msg.role == "user" else "#f9fafb"
        align = "right" if msg.role == "user" else "left"
        transcript_rows += f"""
        <tr>
          <td style="padding:8px 12px;background:{bg};border-radius:8px;
                     text-align:{align};margin-bottom:6px;display:block">
            <span style="font-size:11px;font-weight:600;color:#6b7280;
                         text-transform:uppercase;letter-spacing:0.5px">
              {role_label}
            </span><br/>
            <span style="font-size:14px;color:#111827;line-height:1.5">
              {msg.content.replace(chr(10), "<br/>")}
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
                  {body.name or "Not provided"}
                </span>
              </td>
            </tr>
            <tr>
              <td style="padding:10px 0;border-bottom:1px solid #e5e7eb">
                <span style="font-size:12px;color:#6b7280;font-weight:600;
                             text-transform:uppercase">Email</span><br/>
                <a href="mailto:{body.email}"
                   style="font-size:15px;color:#1d4ed8">
                  {body.email}
                </a>
              </td>
            </tr>
            <tr>
              <td style="padding:10px 0">
                <span style="font-size:12px;color:#6b7280;font-weight:600;
                             text-transform:uppercase">Requirement</span><br/>
                <span style="font-size:15px;color:#111827;line-height:1.6">
                  {body.message}
                </span>
              </td>
            </tr>
          </table>

          {transcript_section}

          <div style="margin-top:28px;padding:16px;background:#f0fdf4;
                      border-radius:8px;border-left:4px solid #16a34a">
            <p style="margin:0;font-size:13px;color:#15803d">
              <strong>Action required:</strong> Reply directly to
              <a href="mailto:{body.email}" style="color:#15803d">
                {body.email}
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


@router.post("/enquiry", response_model=EnquiryResponse)
async def submit_enquiry(body: EnquiryRequest) -> EnquiryResponse:
    settings = get_settings()
    supabase = get_supabase()

    supabase.table("oan_enquiries").insert({
        "name": body.name,
        "email": body.email,
        "message": body.message,
    }).execute()

    resend.api_key = settings.resend_api_key

    resend.Emails.send({
        "from": "Aria — OAN AI <onboarding@resend.dev>",
        "to": [settings.oan_sales_email],
        "reply_to": body.email,
        "subject": f"New Enquiry from {body.name or body.email} — OAN AI",
        "html": build_email_html(body),
    })

    return EnquiryResponse(success=True, message="Enquiry received")