"""
Free Email SMTP Dispatcher for School Management System
Uses Django's email backend for efficient bulk sending.
"""
import logging
from typing import Callable, List, Optional, Tuple
from django.conf import settings
from django.core.mail import get_connection, EmailMessage, EmailMultiAlternatives
from django.core.mail.backends.smtp import EmailBackend
from django.template.loader import render_to_string
from django.utils.html import strip_tags

logger = logging.getLogger(__name__)


class EmailDispatcher:
    """
    SMTP Email Dispatcher using Django's connection pooling.
    Opens a single SMTP connection and reuses it for multiple sends.
    """
    
    def __init__(self, 
                 host: str = None,
                 port: int = None,
                 username: str = None,
                 password: str = None,
                 use_tls: bool = True,
                 fail_silently: bool = False):
        """
        Initialize the email dispatcher with SMTP settings.
        
        Args:
            host: SMTP server hostname
            port: SMTP port (default: 587)
            username: SMTP username (email)
            password: SMTP password/app password
            use_tls: Use TLS encryption (default: True)
            fail_silently: Don't raise exceptions on errors
        """
        self.host = host or getattr(settings, 'EMAIL_HOST', 'smtp.gmail.com')
        self.port = port or getattr(settings, 'EMAIL_PORT', 587)
        self.username = username or getattr(settings, 'EMAIL_HOST_USER', '')
        self.password = password or getattr(settings, 'EMAIL_HOST_PASSWORD', '')
        self.use_tls = use_tls
        self.fail_silently = fail_silently
        self.connection = None
    
    def open_connection(self) -> bool:
        """
        Open a single SMTP connection.
        Returns True if successful, False otherwise.
        """
        try:
            self.connection = get_connection(
                backend_class=EmailBackend,
                host=self.host,
                port=self.port,
                username=self.username,
                password=self.password,
                use_tls=self.use_tls,
                fail_silently=self.fail_silently
            )
            self.connection.open()
            logger.info(f"SMTP connection opened to {self.host}:{self.port}")
            return True
        except Exception as e:
            logger.error(f"Failed to open SMTP connection: {e}")
            return False
    
    def close_connection(self):
        """Close the SMTP connection."""
        if self.connection:
            try:
                self.connection.close()
                logger.info("SMTP connection closed")
            except Exception as e:
                logger.error(f"Error closing SMTP connection: {e}")
    
    def send_email(self, 
                   to_email: str,
                   subject: str,
                   body: str,
                   html_body: str = None,
                   from_email: str = None,
                   attachments: list = None,
                   cc: List[str] = None,
                   bcc: List[str] = None) -> Tuple[bool, str]:
        """
        Send a single email through the connection.
        
        Returns: (success, message)
        """
        if not self.connection:
            return False, "Connection not open"
        
        try:
            from_email = from_email or self.username
            
            if html_body:
                email = EmailMultiAlternatives(
                    subject=subject,
                    body=strip_tags(html_body),
                    from_email=from_email,
                    to=[to_email],
                    cc=cc,
                    bcc=bcc,
                    connection=self.connection
                )
                email.attach_alternative(html_body, 'text/html')
            else:
                email = EmailMessage(
                    subject=subject,
                    body=body,
                    from_email=from_email,
                    to=[to_email],
                    cc=cc,
                    bcc=bcc,
                    connection=self.connection
                )
            
            if attachments:
                for attachment in attachments:
                    if isinstance(attachment, tuple):
                        email.attach(*attachment)
                    else:
                        email.attach(attachment)
            
            email.send(fail_silently=self.fail_silently)
            logger.info(f"Email sent to {to_email}")
            return True, f"Email sent to {to_email}"
            
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")
            return False, str(e)
    
    def __enter__(self):
        """Context manager entry."""
        self.open_connection()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close_connection()
        return False


def send_bulk_individual_emails(
    subject: str,
    template_body_func: Callable,
    student_queryset,
    from_email: str = None,
    batch_size: int = 50,
    delay_between_batches: float = 2.0
) -> dict:
    """
    Send individual, separate emails to each recipient without revealing
    other recipients' email addresses (BCC approach).
    
    Args:
        subject: Email subject line
        template_body_func: Callback function(student) -> (text_body, html_body, recipient_email)
                           Returns tuple of (plain text, HTML body, parent email)
        student_queryset: QuerySet of Student objects
        from_email: Sender email address
        batch_size: Number of emails per batch
        delay_between_batches: Seconds to wait between batches
    
    Returns:
        dict with keys: total, sent, failed, errors
    """
    import time
    from django.conf import settings
    
    results = {
        'total': 0,
        'sent': 0,
        'failed': 0,
        'errors': []
    }
    
    # Get email settings
    host = getattr(settings, 'EMAIL_HOST', 'smtp.gmail.com')
    port = getattr(settings, 'EMAIL_PORT', 587)
    username = getattr(settings, 'EMAIL_HOST_USER', '')
    password = getattr(settings, 'EMAIL_HOST_PASSWORD', '')
    use_tls = getattr(settings, 'EMAIL_USE_TLS', True)
    
    if not username or not password:
        logger.warning("Email credentials not configured")
        results['errors'].append("Email credentials not configured")
        return results
    
    # Process in batches
    students = list(student_queryset)
    total_students = len(students)
    results['total'] = total_students
    
    logger.info(f"Starting bulk email send to {total_students} recipients")
    
    for i in range(0, total_students, batch_size):
        batch = students[i:i + batch_size]
        
        with EmailDispatcher(
            host=host,
            port=port,
            username=username,
            password=password,
            use_tls=use_tls
        ) as dispatcher:
            for student in batch:
                try:
                    # Get email content for this student
                    text_body, html_body, recipient_email = template_body_func(student)
                    
                    if not recipient_email:
                        results['failed'] += 1
                        results['errors'].append(f"No email for {student.student_id}")
                        continue
                    
                    # Send individual email
                    success, message = dispatcher.send_email(
                        to_email=recipient_email,
                        subject=subject,
                        body=text_body,
                        html_body=html_body,
                        from_email=from_email
                    )
                    
                    if success:
                        results['sent'] += 1
                        logger.info(f"Sent to {recipient_email}")
                    else:
                        results['failed'] += 1
                        results['errors'].append(f"{student.student_id}: {message}")
                
                except Exception as e:
                    results['failed'] += 1
                    results['errors'].append(f"{student.student_id}: {str(e)}")
                    logger.error(f"Error sending to {student.student_id}: {e}")
        
        # Delay between batches to avoid rate limiting
        if i + batch_size < total_students:
            time.sleep(delay_between_batches)
    
    logger.info(f"Bulk email complete: {results['sent']}/{total_students} sent")
    return results


def send_single_email(
    to_email: str,
    subject: str,
    body: str,
    html_body: str = None,
    from_email: str = None
) -> Tuple[bool, str]:
    """
    Convenience function to send a single email.
    
    Returns: (success, message)
    """
    with EmailDispatcher() as dispatcher:
        return dispatcher.send_email(
            to_email=to_email,
            subject=subject,
            body=body,
            html_body=html_body,
            from_email=from_email
        )


def get_email_template_context(student, extra_data: dict = None) -> dict:
    """
    Get common context variables for email templates.
    
    Returns a dictionary with student and school info.
    """
    context = {
        'student': student,
        'student_name': f"{student.first_name} {student.last_name}",
        'student_id': student.student_id,
        'current_class': student.current_class,
        'school_name': student.school.school_name if student.school else 'School',
        'guardian_name': student.guardian_name or 'Parent/Guardian',
        'academic_year': student.school.active_academic_year if student.school else '',
        'term': student.school.active_term if student.school else '',
    }
    
    if extra_data:
        context.update(extra_data)
    
    return context


# ============================================================================
# REPORT CARD EMAIL FUNCTION
# ============================================================================

def send_report_card_email(student, pdf_attachment=None) -> Tuple[bool, str]:
    """
    Send a report card email to a student's parent.
    
    Args:
        student: Student model instance
        pdf_attachment: Path to PDF file (optional)
    
    Returns: (success, message)
    """
    from django.template.loader import render_to_string
    
    subject = f"Report Card - {student.first_name} {student.last_name} ({student.school.active_term}, {student.school.active_academic_year})"
    
    context = get_email_template_context(student)
    
    try:
        html_body = render_to_string('notifications/report_card_email.html', context)
        text_body = f"""
Dear {context['guardian_name']},

Please find attached the report card for {context['student_name']} for {context['term']}, {context['academic_year']}.

Student ID: {context['student_id']}
Class: {context['current_class']}

Please contact the school if you have any questions.

Best regards,
{context['school_name']}
"""
        
        attachments = []
        if pdf_attachment:
            attachments.append(('Report_Card.pdf', pdf_attachment, 'application/pdf'))
        
        return send_single_email(
            to_email=student.guardian_email,
            subject=subject,
            body=text_body,
            html_body=html_body
        )
    except Exception as e:
        return False, str(e)


# ============================================================================
# FEE REMINDER EMAIL FUNCTION
# ============================================================================

def send_fee_reminder_email(student, balance: float) -> Tuple[bool, str]:
    """
    Send a fee balance reminder email to a student's parent.
    """
    from django.template.loader import render_to_string
    from django.utils import timezone
    
    subject = f"Fee Payment Reminder - {student.first_name} {student.last_name}"
    
    context = get_email_template_context(student, {
        'balance': balance,
        'balance_formatted': f"UGX {balance:,.0f}",
        'date': timezone.now().strftime('%B %d, %Y')
    })
    
    try:
        html_body = render_to_string('notifications/fee_reminder_email.html', context)
        text_body = f"""
Dear {context['guardian_name']},

This is a friendly reminder that there is an outstanding fee balance for {context['student_name']}.

Current Balance: {context['balance_formatted']}
Date: {context['date']}

Please arrange for payment at your earliest convenience.

Best regards,
{context['school_name']}
"""
        
        return send_single_email(
            to_email=student.guardian_email,
            subject=subject,
            body=text_body,
            html_body=html_body
        )
    except Exception as e:
        return False, str(e)


if __name__ == '__main__':
    # Test email configuration
    print("Email Dispatcher Test")
    print("=" * 50)
    
    with EmailDispatcher() as dispatcher:
        print(f"Connection open: {dispatcher.connection is not None}")
        print(f"Host: {dispatcher.host}:{dispatcher.port}")
        print(f"Username: {dispatcher.username}")
