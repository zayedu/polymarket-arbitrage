"""
Email notification module using SendGrid for alerting on arbitrage opportunities.
"""
import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional
import os

try:
    from sendgrid import SendGridAPIClient
    from sendgrid.helpers.mail import Mail, Email, To, Content
    SENDGRID_AVAILABLE = True
except ImportError:
    SENDGRID_AVAILABLE = False
    logging.warning("SendGrid not installed. Email notifications will be disabled. Install with: pip install sendgrid")

from .models import ArbitrageOpportunity

logger = logging.getLogger(__name__)


class EmailNotifier:
    """Sends email notifications for arbitrage opportunities and system events."""
    
    # SMS carrier gateways for email-to-SMS
    SMS_GATEWAYS = {
        "rogers": "pcs.rogers.com",
        "bell": "txt.bell.ca",
        "telus": "msg.telus.com",
        "fido": "fido.ca",
        "koodo": "msg.koodomobile.com",
        "freedom": "txt.freedommobile.ca"
    }
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        from_email: Optional[str] = None,
        to_email: Optional[str] = None,
        enabled: bool = True,
        sms_enabled: bool = False,
        sms_phone_number: Optional[str] = None,
        sms_carrier: Optional[str] = None
    ):
        """
        Initialize email notifier.
        
        Args:
            api_key: SendGrid API key
            from_email: Sender email address
            to_email: Recipient email address
            enabled: Whether notifications are enabled
            sms_enabled: Whether SMS notifications are enabled
            sms_phone_number: Phone number for SMS (digits only)
            sms_carrier: Carrier name (rogers, bell, telus, etc.)
        """
        self.enabled = enabled and SENDGRID_AVAILABLE
        self.api_key = api_key
        self.from_email = from_email or "bot@polymarket-arbitrage.com"
        self.to_email = to_email
        
        # SMS configuration
        self.sms_enabled = sms_enabled and SENDGRID_AVAILABLE
        self.sms_phone_number = sms_phone_number
        self.sms_carrier = sms_carrier.lower() if sms_carrier else None
        self.sms_email = None
        
        if not self.enabled:
            logger.warning("Email notifications are DISABLED")
            return
        
        if not api_key:
            logger.error("SendGrid API key not provided. Email notifications disabled.")
            self.enabled = False
            return
        
        if not to_email:
            logger.error("Recipient email not provided. Email notifications disabled.")
            self.enabled = False
            return
        
        try:
            self.client = SendGridAPIClient(api_key)
            logger.info(f"✅ Email notifier initialized. Alerts will be sent to: {to_email}")
            
            # Setup SMS if enabled
            if self.sms_enabled and sms_phone_number and sms_carrier:
                if sms_carrier in self.SMS_GATEWAYS:
                    self.sms_email = f"{sms_phone_number}@{self.SMS_GATEWAYS[sms_carrier]}"
                    logger.info(f"✅ SMS notifications enabled. Messages will be sent to: {sms_phone_number} ({sms_carrier})")
                else:
                    logger.warning(f"Unknown SMS carrier: {sms_carrier}. SMS disabled. Valid carriers: {list(self.SMS_GATEWAYS.keys())}")
                    self.sms_enabled = False
            elif self.sms_enabled:
                logger.warning("SMS enabled but phone number or carrier not provided. SMS disabled.")
                self.sms_enabled = False
                
        except Exception as e:
            logger.error(f"Failed to initialize SendGrid client: {e}")
            self.enabled = False
    
    async def send_opportunity_alert(
        self,
        opportunities: List[ArbitrageOpportunity],
        max_opportunities: int = 5
    ) -> bool:
        """
        Send email alert for detected arbitrage opportunities.
        
        Args:
            opportunities: List of arbitrage opportunities
            max_opportunities: Maximum number to include in email
            
        Returns:
            True if email sent successfully
        """
        if not self.enabled:
            return False
        
        if not opportunities:
            return False
        
        try:
            # Limit opportunities to display
            top_opportunities = opportunities[:max_opportunities]
            
            # Build email content
            subject = f"🚨 {len(opportunities)} Arbitrage Opportunit{'y' if len(opportunities) == 1 else 'ies'} Detected!"
            html_content = self._build_opportunity_email(top_opportunities, len(opportunities))
            
            # Send email
            message = Mail(
                from_email=Email(self.from_email),
                to_emails=To(self.to_email),
                subject=subject,
                html_content=Content("text/html", html_content)
            )
            
            response = self.client.send(message)
            
            if response.status_code in [200, 201, 202]:
                logger.info(f"📧 Sent opportunity alert email to {self.to_email}")
                return True
            else:
                logger.error(f"Failed to send email. Status code: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending opportunity alert: {e}")
            return False
    
    def _build_opportunity_email(
        self,
        opportunities: List[ArbitrageOpportunity],
        total_count: int
    ) -> str:
        """Build HTML email content for opportunities."""
        
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        
        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .header {{ background-color: #4CAF50; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; }}
                .opportunity {{ 
                    border: 1px solid #ddd; 
                    border-radius: 5px; 
                    padding: 15px; 
                    margin: 15px 0;
                    background-color: #f9f9f9;
                }}
                .opportunity h3 {{ margin-top: 0; color: #4CAF50; }}
                .metric {{ display: inline-block; margin-right: 20px; }}
                .metric-label {{ font-weight: bold; color: #666; }}
                .metric-value {{ color: #333; }}
                .profit {{ color: #4CAF50; font-weight: bold; }}
                .apy {{ color: #2196F3; font-weight: bold; }}
                .link {{ 
                    display: inline-block;
                    margin-top: 10px;
                    padding: 8px 16px;
                    background-color: #4CAF50;
                    color: white;
                    text-decoration: none;
                    border-radius: 4px;
                }}
                .footer {{ 
                    margin-top: 30px; 
                    padding-top: 20px; 
                    border-top: 1px solid #ddd;
                    color: #666;
                    font-size: 12px;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🚨 Arbitrage Alert</h1>
                <p>{timestamp}</p>
            </div>
            <div class="content">
                <p><strong>{total_count} arbitrage opportunit{'y' if total_count == 1 else 'ies'} detected!</strong></p>
                <p>Top {len(opportunities)} opportunit{'y' if len(opportunities) == 1 else 'ies'} shown below:</p>
        """
        
        for i, opp in enumerate(opportunities, 1):
            # Build Polymarket URL
            market_slug = opp.market.title.lower().replace(' ', '-').replace('?', '')[:50]
            polymarket_url = f"https://polymarket.com/event/{market_slug}"
            
            html += f"""
                <div class="opportunity">
                    <h3>#{i}: {opp.market.title}</h3>
                    <div class="metric">
                        <span class="metric-label">Type:</span>
                        <span class="metric-value">{opp.opportunity_type.replace('_', ' ').title()}</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">Net Profit:</span>
                        <span class="metric-value profit">${opp.net_profit:.4f}</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">APY:</span>
                        <span class="metric-value apy">{opp.apy:.2f}%</span>
                    </div>
                    <br>
                    <div class="metric">
                        <span class="metric-label">YES Ask:</span>
                        <span class="metric-value">${opp.yes_ask:.4f}</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">NO Ask:</span>
                        <span class="metric-value">${opp.no_ask:.4f}</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">Sum:</span>
                        <span class="metric-value">${(opp.yes_ask + opp.no_ask):.4f}</span>
                    </div>
                    <br>
                    <div class="metric">
                        <span class="metric-label">Gross Edge:</span>
                        <span class="metric-value">${opp.gross_edge:.4f}</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">Capital Required:</span>
                        <span class="metric-value">${opp.required_capital:.2f}</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">Liquidity:</span>
                        <span class="metric-value">${opp.top_of_book_depth:.2f}</span>
                    </div>
                    <br>
                    <div class="metric">
                        <span class="metric-label">Days to Resolution:</span>
                        <span class="metric-value">{opp.market.days_to_resolution}</span>
                    </div>
                    <a href="{polymarket_url}" class="link" target="_blank">View on Polymarket →</a>
                </div>
            """
        
        html += """
                <div class="footer">
                    <p><strong>⚠️ Important:</strong></p>
                    <ul>
                        <li>Verify opportunities on Polymarket before executing</li>
                        <li>Consider slippage and gas costs</li>
                        <li>Opportunities may disappear quickly</li>
                        <li>This is an automated alert - not financial advice</li>
                    </ul>
                    <p>Polymarket Arbitrage Bot | Notification System</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return html
    
    async def send_health_check(self, stats: Optional[dict] = None) -> bool:
        """
        Send daily health check email.
        
        Args:
            stats: Optional statistics dictionary
            
        Returns:
            True if email sent successfully
        """
        if not self.enabled:
            return False
        
        try:
            timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
            
            subject = "✅ Arbitrage Bot Daily Health Check"
            
            html_content = f"""
            <html>
            <body style="font-family: Arial, sans-serif;">
                <div style="background-color: #2196F3; color: white; padding: 20px; text-align: center;">
                    <h1>✅ Bot Health Check</h1>
                    <p>{timestamp}</p>
                </div>
                <div style="padding: 20px;">
                    <p>Your Polymarket arbitrage bot is running successfully.</p>
                    <h3>Status:</h3>
                    <ul>
                        <li>✅ Bot is online and scanning</li>
                        <li>✅ API connections healthy</li>
                        <li>✅ Database operational</li>
                    </ul>
            """
            
            if stats:
                html_content += "<h3>24-Hour Statistics:</h3><ul>"
                for key, value in stats.items():
                    html_content += f"<li>{key}: {value}</li>"
                html_content += "</ul>"
            
            html_content += """
                    <p style="color: #666; font-size: 12px; margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd;">
                        This is an automated health check. You will receive alerts if opportunities are found.
                    </p>
                </div>
            </body>
            </html>
            """
            
            message = Mail(
                from_email=Email(self.from_email),
                to_emails=To(self.to_email),
                subject=subject,
                html_content=Content("text/html", html_content)
            )
            
            response = self.client.send(message)
            
            if response.status_code in [200, 201, 202]:
                logger.info(f"📧 Sent health check email to {self.to_email}")
                return True
            else:
                logger.error(f"Failed to send health check. Status code: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending health check: {e}")
            return False
    
    async def send_error_alert(self, error_message: str, traceback: Optional[str] = None) -> bool:
        """
        Send email alert for critical errors.
        
        Args:
            error_message: Error message
            traceback: Optional traceback string
            
        Returns:
            True if email sent successfully
        """
        if not self.enabled:
            return False
        
        try:
            timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
            
            subject = "🚨 CRITICAL: Arbitrage Bot Error"
            
            html_content = f"""
            <html>
            <body style="font-family: Arial, sans-serif;">
                <div style="background-color: #f44336; color: white; padding: 20px; text-align: center;">
                    <h1>🚨 Critical Error</h1>
                    <p>{timestamp}</p>
                </div>
                <div style="padding: 20px;">
                    <p><strong>Your arbitrage bot encountered a critical error:</strong></p>
                    <div style="background-color: #ffebee; padding: 15px; border-left: 4px solid #f44336; margin: 20px 0;">
                        <code>{error_message}</code>
                    </div>
            """
            
            if traceback:
                html_content += f"""
                    <h3>Traceback:</h3>
                    <pre style="background-color: #f5f5f5; padding: 15px; overflow-x: auto; font-size: 12px;">
{traceback}
                    </pre>
                """
            
            html_content += """
                    <p><strong>Action Required:</strong></p>
                    <ul>
                        <li>Check bot logs for details</li>
                        <li>Verify API credentials and connections</li>
                        <li>Restart the bot if necessary</li>
                    </ul>
                </div>
            </body>
            </html>
            """
            
            message = Mail(
                from_email=Email(self.from_email),
                to_emails=To(self.to_email),
                subject=subject,
                html_content=Content("text/html", html_content)
            )
            
            response = self.client.send(message)
            
            if response.status_code in [200, 201, 202]:
                logger.info(f"📧 Sent error alert email to {self.to_email}")
                return True
            else:
                logger.error(f"Failed to send error alert. Status code: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending error alert: {e}")
            return False
    
    async def send_sms(self, message: str, max_length: int = 140) -> bool:
        """
        Send SMS notification via email-to-SMS gateway.
        
        Args:
            message: Text message to send (will be truncated to max_length)
            max_length: Maximum message length (default 140 chars for SMS)
            
        Returns:
            True if SMS sent successfully
        """
        if not self.sms_enabled or not self.sms_email:
            logger.debug("SMS not enabled or not configured")
            return False
        
        try:
            # Truncate message to SMS length
            truncated_message = message[:max_length]
            
            # Send as plain text email to SMS gateway
            mail_message = Mail(
                from_email=Email(self.from_email),
                to_emails=To(self.sms_email),
                subject="",  # Subject often ignored by SMS gateways
                plain_text_content=Content("text/plain", truncated_message)
            )
            
            response = self.client.send(mail_message)
            
            if response.status_code in [200, 201, 202]:
                logger.info(f"📱 Sent SMS to {self.sms_phone_number}")
                return True
            else:
                logger.error(f"Failed to send SMS. Status code: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending SMS: {e}")
            return False


