"""
Notification Models for WhatsApp Queue and Message Tracking
"""
from django.db import models
from django.utils import timezone


class WhatsAppMessage(models.Model):
    """
    Track WhatsApp messages sent through the queue system.
    """
    
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('QUEUED', 'Queued'),
        ('SENT', 'Sent'),
        ('FAILED', 'Failed'),
        ('OPENED', 'Opened'),
    ]
    
    MESSAGE_TYPE_CHOICES = [
        ('FEE_REMINDER', 'Fee Reminder'),
        ('REPORT_CARD', 'Report Card'),
        ('GENERAL', 'General Notice'),
        ('ATTENDANCE', 'Attendance Notice'),
        ('MEETING', 'Meeting Notice'),
    ]
    
    student = models.ForeignKey(
        'core.Student',
        on_delete=models.CASCADE,
        related_name='whatsapp_messages'
    )
    parent_phone = models.CharField(max_length=20)
    parent_name = models.CharField(max_length=200)
    message_type = models.CharField(
        max_length=20, 
        choices=MESSAGE_TYPE_CHOICES,
        default='GENERAL'
    )
    message_content = models.TextField()
    wa_link = models.URLField(
        max_length=500,
        help_text="Pre-generated WhatsApp URL"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='QUEUED'
    )
    sent_at = models.DateTimeField(null=True, blank=True)
    opened_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    created_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='whatsapp_messages'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "WhatsApp Message"
        verbose_name_plural = "WhatsApp Messages"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['student', 'message_type']),
        ]
    
    def __str__(self):
        return f"{self.parent_name} - {self.message_type} ({self.status})"
    
    def mark_as_sent(self):
        """Mark message as sent."""
        self.status = 'SENT'
        self.sent_at = timezone.now()
        self.save()
    
    def mark_as_failed(self, error: str = ''):
        """Mark message as failed."""
        self.status = 'FAILED'
        self.error_message = error
        self.save()
    
    @property
    def formatted_phone(self):
        """Format phone number for display."""
        phone = self.parent_phone.strip()
        if not phone.startswith('+'):
            phone = '+' + phone
        return phone


class EmailMessage(models.Model):
    """
    Track emails sent through the system.
    """
    
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('SENT', 'Sent'),
        ('FAILED', 'Failed'),
        ('OPENED', 'Opened'),
    ]
    
    student = models.ForeignKey(
        'core.Student',
        on_delete=models.CASCADE,
        related_name='email_messages'
    )
    recipient_email = models.EmailField()
    subject = models.CharField(max_length=255)
    body = models.TextField()
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDING'
    )
    sent_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    created_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='email_messages'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Email Message"
        verbose_name_plural = "Email Messages"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.recipient_email} - {self.subject[:30]}"


class NotificationTemplate(models.Model):
    """
    Reusable notification templates.
    """
    
    name = models.CharField(max_length=100, unique=True)
    message_type = models.CharField(max_length=20)
    subject = models.CharField(max_length=255, blank=True)
    template_content = models.TextField(
        help_text="Use {student_name}, {guardian_name}, {class_name}, etc."
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Notification Template"
        verbose_name_plural = "Notification Templates"
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.message_type})"
    
    def render(self, context: dict) -> str:
        """Render template with context variables."""
        import string
        template = string.Template(self.template_content)
        return template.safe_substitute(context)


class NotificationBatch(models.Model):
    """
    Track bulk notification batches.
    """
    
    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('SENDING', 'Sending'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
    ]
    
    CHANNEL_CHOICES = [
        ('WHATSAPP', 'WhatsApp'),
        ('EMAIL', 'Email'),
        ('BOTH', 'Both'),
    ]
    
    name = models.CharField(max_length=100)
    channel = models.CharField(
        max_length=20,
        choices=CHANNEL_CHOICES,
        default='WHATSAPP'
    )
    template = models.ForeignKey(
        NotificationTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    student_count = models.PositiveIntegerField(default=0)
    sent_count = models.PositiveIntegerField(default=0)
    failed_count = models.PositiveIntegerField(default=0)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='DRAFT'
    )
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='notification_batches'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = "Notification Batch"
        verbose_name_plural = "Notification Batches"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} ({self.get_status_display()})"
    
    @property
    def progress_percent(self):
        """Calculate sending progress."""
        if self.student_count == 0:
            return 0
        return int((self.sent_count / self.student_count) * 100)
