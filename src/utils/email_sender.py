"""
Email Service for AX5 Plotter Photo Booth

Sends processed images to users via email.
"""

import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from pathlib import Path
from typing import Optional
import yaml

logger = logging.getLogger(__name__)


class EmailSender:
    """Handles sending emails with processed images."""
    
    def __init__(self, config_path: str = "config/settings.yaml"):
        self.config = self._load_config(config_path)
        self.enabled = self.config.get('email', {}).get('enabled', False)
        
        if self.enabled:
            self.smtp_server = self.config['email']['smtp_server']
            self.smtp_port = self.config['email']['smtp_port']
            self.smtp_username = self.config['email']['smtp_username']
            self.smtp_password = self.config['email']['smtp_password']
            self.from_email = self.config['email']['from_email']
            self.from_name = self.config['email'].get('from_name', 'AX5 Plotter Photo Booth')
        else:
            logger.warning("Email service disabled in configuration")
    
    def _load_config(self, config_path: str) -> dict:
        """Load configuration from YAML file."""
        try:
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            return {}
    
    def send_image(
        self,
        to_email: str,
        to_name: str,
        image_path: str,
        style: str,
        subject: Optional[str] = None
    ) -> bool:
        """
        Send processed image to user.
        
        Args:
            to_email: Recipient email address
            to_name: Recipient name
            image_path: Path to processed image
            style: Image style used
            subject: Optional custom subject line
            
        Returns:
            bool: True if sent successfully
        """
        if not self.enabled:
            logger.info(f"Email disabled, would send to {to_email}")
            return False
        
        try:
            # Create message
            msg = MIMEMultipart('related')
            msg['From'] = f"{self.from_name} <{self.from_email}>"
            msg['To'] = f"{to_name} <{to_email}>"
            msg['Subject'] = subject or f"Your {style} Portrait from AX5 Plotter Photo Booth"
            
            # HTML body
            html_body = f"""
            <html>
            <body style="font-family: Arial, sans-serif; padding: 20px; background-color: #f5f5f5;">
                <div style="max-width: 600px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
                    <h2 style="color: #333; margin-bottom: 20px;">Hi {to_name}! 👋</h2>
                    
                    <p style="color: #666; line-height: 1.6;">
                        Thank you for visiting our AX5 Plotter Photo Booth! Here's your <strong>{style}</strong> portrait, 
                        lovingly drawn by our robotic plotter.
                    </p>
                    
                    <div style="margin: 30px 0; text-align: center;">
                        <img src="cid:processed_image" style="max-width: 100%; height: auto; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.15);" alt="Your portrait">
                    </div>
                    
                    <p style="color: #666; line-height: 1.6; margin-top: 30px;">
                        We hope you enjoyed the experience! Feel free to share this unique artwork with your friends.
                    </p>
                    
                    <div style="margin-top: 40px; padding-top: 20px; border-top: 1px solid #eee; text-align: center; color: #999; font-size: 12px;">
                        <p>Created with ❤️ by AX5 Plotter Photo Booth</p>
                        <p>Powered by AI and precision robotics</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            msg.attach(MIMEText(html_body, 'html'))
            
            # Attach image
            with open(image_path, 'rb') as f:
                img_data = f.read()
                image = MIMEImage(img_data, name=Path(image_path).name)
                image.add_header('Content-ID', '<processed_image>')
                msg.attach(image)
            
            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)
            
            logger.info(f"Email sent successfully to {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")
            return False
    
    def test_connection(self) -> bool:
        """Test SMTP connection."""
        if not self.enabled:
            logger.warning("Email service is disabled")
            return False
        
        try:
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
            
            logger.info("Email connection test successful")
            return True
            
        except Exception as e:
            logger.error(f"Email connection test failed: {e}")
            return False
