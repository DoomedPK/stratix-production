from django.db import models
from django.contrib.auth.models import User, Group
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import secrets
import os

class Client(models.Model):
    name = models.CharField(max_length=200, unique=True)
    email = models.EmailField(max_length=254, null=True, blank=True)
    location = models.CharField(max_length=100, default='Unknown')

    def __str__(self):
        return self.name

class Project(models.Model):
    name = models.CharField(max_length=200, unique=True)
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='projects')
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=[('Active', 'Active'), ('Completed', 'Completed')], default='Active')
    
    PROJECT_TYPE_CHOICES = [
        ('General', 'General Maintenance'),
        ('Post-Disaster', 'Post-Disaster Emergency Response')
    ]
    project_type = models.CharField(max_length=50, choices=PROJECT_TYPE_CHOICES, default='General')
    require_photo_minimums = models.BooleanField(default=False, help_text="Enforce minimum photo counts per category for contractors.")

    # 🚀 NEW: Dynamic Photo Minimums (Defaults set to your standard rules)
    min_site_overview = models.IntegerField(default=4, verbose_name="Min Site Overview")
    min_access_road = models.IntegerField(default=2, verbose_name="Min Access Road")
    min_tower_structure = models.IntegerField(default=5, verbose_name="Min Tower Structure")
    min_tower_base = models.IntegerField(default=14, verbose_name="Min Tower Base & Foundation")
    min_antennas = models.IntegerField(default=9, verbose_name="Min Antennas & Mounting")
    min_cabling = models.IntegerField(default=3, verbose_name="Min Cabling & Connections")
    min_equipment_shelter = models.IntegerField(default=2, verbose_name="Min Equipment Shelter")
    min_power_systems = models.IntegerField(default=2, verbose_name="Min Power Systems")
    min_grounding = models.IntegerField(default=2, verbose_name="Min Grounding")
    min_perimeter = models.IntegerField(default=5, verbose_name="Min Perimeter & Security")
    min_additional = models.IntegerField(default=0, verbose_name="Min Additional Observations")

    def get_photo_minimums(self):
        """Returns a dictionary of this specific project's minimums."""
        return {
            'Site Overview': self.min_site_overview,
            'Access Road': self.min_access_road,
            'Tower Structure': self.min_tower_structure,
            'Tower Base & Foundation': self.min_tower_base,
            'Antennas & Mounting Systems': self.min_antennas,
            'Cabling & Connections': self.min_cabling,
            'Equipment Shelter / Cabinets': self.min_equipment_shelter,
            'Power Systems': self.min_power_systems,
            'Grounding & Earthing': self.min_grounding,
            'Perimeter, Security & Surroundings': self.min_perimeter,
            'Additional Observations': self.min_additional,
        }

    def __str__(self):
        return f"{self.name} ({self.project_type})"

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    client = models.ForeignKey(Client, on_delete=models.SET_NULL, null=True, blank=True)
    role = models.CharField(max_length=50, choices=[
        ('Admin', 'Admin'), 
        ('Client', 'Client'), 
        ('Contractor', 'Contractor'),
        ('QA', 'QA'),
        ('Tech Writer', 'Technical Report Writer'), 
    ], default='Client')
    has_seen_tutorial = models.BooleanField(default=False)
    
    welcome_email_sent = models.BooleanField(default=False) 

    def __str__(self):
        return f"{self.user.username} - {self.get_role_display()}"

class Site(models.Model):
    site_id = models.CharField(max_length=100, unique=True)
    site_name = models.CharField(max_length=200)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='sites')
    location = models.CharField(max_length=255)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    assigned_contractors = models.ManyToManyField(User, blank=True, related_name='assigned_sites')
    criticality_level = models.CharField(max_length=20, choices=[('Low', 'Low'), ('Medium', 'Medium'), ('High', 'High Priority Node')], default='Medium')
    priority = models.CharField(max_length=20, choices=[('Low', 'Low'), ('Medium', 'Medium'), ('High', 'High')], default='Medium')
    height_in_meters = models.FloatField(null=True, blank=True, help_text="Site height in meters")

    # 🚀 NEW: Client-Provided Design Data
    tower_type = models.CharField(max_length=100, blank=True, null=True, help_text="e.g., Monopole, Lattice, Guyed Mast, Rooftop")
    expected_antenna_count = models.IntegerField(blank=True, null=True, help_text="Total number of antennas the client expects on site")
    expected_azimuth = models.CharField(max_length=100, blank=True, null=True, help_text="e.g., Sector A: 120°, Sector B: 240°")
    expected_tilt = models.CharField(max_length=100, blank=True, null=True, help_text="e.g., 4° downtilt on all sectors")
    sector_layout = models.CharField(max_length=100, blank=True, null=True, help_text="e.g., 3 Sectors, Huawei AAU panels")

    def __str__(self):
        return f"{self.site_id} - {self.site_name}"

class Report(models.Model):
    site = models.ForeignKey(Site, on_delete=models.CASCADE, related_name='reports')
    submitted_at = models.DateTimeField(auto_now_add=True)
    comments = models.TextField(blank=True)
    final_document = models.FileField(upload_to='final_reports/%Y/%m/', blank=True, null=True)

    STATUS_CHOICES = [
        ('not_visited', 'Not Visited'),
        ('visit_in_progress', 'Visit In Progress'),
        ('qa_validation', 'QA Validation'),
        ('site_data_submitted', 'Site Data Submitted'),
        ('engineer_review', 'Report in Progress'),
        ('submitted', 'Submitted'),
    ]
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='not_visited')

    structural_risk_score = models.IntegerField(null=True, blank=True)
    equipment_damage_score = models.IntegerField(null=True, blank=True)
    urgency_flag = models.CharField(max_length=20, choices=[('Low', 'Defer Action'), ('Medium', 'Routine Maintenance'), ('High', 'Immediate Repair')], default='Low')
    ai_repair_timeline = models.CharField(max_length=100, blank=True, null=True)
    ai_resource_suggestion = models.TextField(blank=True, null=True)
    
    client_executive_summary = models.TextField(blank=True, null=True)
    historical_trend_analysis = models.TextField(blank=True, null=True)
    category_damage_breakdown = models.TextField(blank=True, null=True)
    
    predictive_risk_outlook = models.TextField(blank=True, null=True, help_text="AI simulation of future structural degradation based on environment.")
    drone_3d_model_link = models.URLField(max_length=500, blank=True, null=True, help_text="Public share link from DroneDeploy or Pix4D.")

    def __str__(self):
        return f"Report for {self.site.site_id}"

class SitePhoto(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending Validation'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rework Required'),
    ]
    CATEGORY_CHOICES = [
        ('Site Overview', 'Site Overview (Min: 4)'),
        ('Access Road', 'Access Road (Min: 2)'),
        ('Tower Structure', 'Tower Structure (Min: 5)'),
        ('Tower Base & Foundation', 'Tower Base & Foundation (Min: 14)'),
        ('Antennas & Mounting Systems', 'Antennas & Mounting Systems (Min: 9)'),
        ('Cabling & Connections', 'Cabling & Connections (Min: 3)'),
        ('Equipment Shelter / Cabinets', 'Equipment Shelter / Cabinets (Min: 2)'),
        ('Power Systems', 'Power Systems (Min: 2)'),
        ('Grounding & Earthing', 'Grounding & Earthing (Min: 2)'),
        ('Perimeter, Security & Surroundings', 'Perimeter, Security & Surroundings (Min: 5)'),
        ('Additional Observations', 'Additional Observations (Optional)'),
    ]

    site = models.ForeignKey(Site, on_delete=models.CASCADE, related_name='photos')
    contractor = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'groups__name': 'Contractors'})
    image = models.ImageField(upload_to='site_photos/%Y/%m/%d/')
    
    annotated_image = models.ImageField(upload_to='annotated_photos/%Y/%m/%d/', blank=True, null=True, help_text="AI-drawn bounding boxes of damage.")
    is_drone_capture = models.BooleanField(default=False, help_text="True if uploaded via the Automated Drone API.")

    category = models.CharField(max_length=100, choices=CATEGORY_CHOICES, default='Site Overview')
    contractor_notes = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    qa_feedback = models.TextField(blank=True, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    ai_tags = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"Photo for {self.site.site_id} - {self.status}"

class ActivityAlert(models.Model):
    message = models.CharField(max_length=255)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='triggered_alerts')
    site = models.ForeignKey(Site, on_delete=models.CASCADE, related_name='site_alerts')
    timestamp = models.DateTimeField(auto_now_add=True)
    
    alert_type = models.CharField(max_length=50, choices=[
        ('CHECK_IN', 'Contractor Checked In'),
        ('UPLOAD', 'Photos/Reports Uploaded'),
        ('REWORK', 'Rework Requested'),
        ('AI_ALERT', 'AI Critical Risk Detected'),
    ], default='CHECK_IN')

    def __str__(self):
        return f"[{self.timestamp.strftime('%Y-%m-%d %H:%M')}] {self.user.username}: {self.message}"

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.get_or_create(user=instance)

@receiver(post_save, sender=UserProfile)
def sync_role_and_group(sender, instance, **kwargs):
    role_to_group = {
        'Admin': 'Admins',
        'Client': 'Clients',
        'Contractor': 'Contractors',
        'QA': 'QAs',
        'Tech Writer': 'Technical Report Writers' 
    }
    group_name = role_to_group.get(instance.role)
    if group_name:
        group, _ = Group.objects.get_or_create(name=group_name)
        instance.user.groups.clear()
        instance.user.groups.add(group)

    if not instance.welcome_email_sent and instance.user.email:
        from django.core.mail import send_mail
        from django.conf import settings

        subject = "Your Stratix Dashboard Credentials"
        message = f"""Hello {instance.user.first_name or instance.user.username},

Your secure access to the Stratix Real-Time Tracking Platform has been activated.

=========================================
ACCOUNT DETAILS
=========================================
Role: {instance.get_role_display()}
Username: {instance.user.username}
Login Portal: https://portal.stratixjm.com

=========================================
HOW TO SET YOUR PASSWORD
=========================================
For security reasons, your password is not transmitted via email. 
To set up your password and log in for the first time:
1. Click the 'Login Portal' link above.
2. Click the yellow 'Forgot Password?' link on the login screen.
3. Enter the email address associated with this account.
4. Follow the link sent to your email to create your permanent password.

SECURITY WARNING: 
This is a secure system. Do not share your credentials with anyone. 

Regards,
Stratix Support Team
"""
        try:
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [instance.user.email],
                fail_silently=True,
            )
            UserProfile.objects.filter(pk=instance.pk).update(welcome_email_sent=True)
        except Exception as e:
            print(f"Email failed to send: {e}")

@receiver(post_save, sender=ActivityAlert)
def trigger_client_fetch(sender, instance, created, **kwargs):
    if created:
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            'global_ping',
            {'type': 'ping_client'}
        )

class SiteIssue(models.Model):
    SEVERITY_CHOICES = [
        ('Minor', 'Minor'),
        ('Major', 'Major'),
        ('Critical', 'Critical'),
    ]
    site = models.ForeignKey(Site, on_delete=models.CASCADE, related_name='issues')
    reported_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    description = models.TextField()
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, default='Minor')
    is_resolved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

class SupportTicket(models.Model):
    STATUS_CHOICES = [('Pending', 'Pending'), ('In Progress', 'In Progress'), ('Resolved', 'Resolved')]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='support_tickets')
    subject = models.CharField(max_length=150)
    description = models.TextField()
    screenshot = models.ImageField(upload_to='support_tickets/%Y/%m/%d/', blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    created_at = models.DateTimeField(auto_now_add=True)

@receiver(pre_delete, sender=SitePhoto)
def auto_delete_photo_on_delete(sender, instance, **kwargs):
    if instance.image:
        instance.image.delete(save=False)
    if instance.annotated_image:
        instance.annotated_image.delete(save=False)

@receiver(pre_delete, sender=Report)
def auto_delete_pdf_on_delete(sender, instance, **kwargs):
    if instance.final_document:
        instance.final_document.delete(save=False)

class AIPromptSettings(models.Model):
    name = models.CharField(max_length=100, default="Gemini Vision Prompt")
    prompt_text = models.TextField()
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "AI Prompt Setting"
        verbose_name_plural = "AI Prompt Settings"

class DroneAPIKey(models.Model):
    contractor = models.OneToOneField(User, on_delete=models.CASCADE, related_name='drone_api_key', limit_choices_to={'groups__name': 'Contractors'})
    key = models.CharField(max_length=100, unique=True, blank=True)
    is_active = models.BooleanField(default=True, help_text="Uncheck this to instantly revoke drone access for this contractor.")
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.key:
            self.key = f"stx_{secrets.token_urlsafe(32)}"
        super().save(*args, **kwargs)

    def __str__(self):
        status = "🟢 Active" if self.is_active else "🔴 Revoked"
        return f"{status} | Key for {self.contractor.username}"
