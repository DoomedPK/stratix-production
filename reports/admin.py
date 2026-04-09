from django.contrib import admin
from .models import Client, Project, UserProfile, Site, Report, SitePhoto, ActivityAlert, SiteIssue, SupportTicket, AIPromptSettings, DroneAPIKey

@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'location')
    search_fields = ('name', 'email')

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'client', 'project_type', 'status', 'require_photo_minimums', 'start_date')
    list_editable = ('project_type', 'status', 'require_photo_minimums')
    list_filter = ('project_type', 'status', 'client')
    search_fields = ('name',)

@admin.register(Site)
class SiteAdmin(admin.ModelAdmin):
    list_display = ('site_id', 'site_name', 'project', 'criticality_level', 'priority')
    list_editable = ('criticality_level', 'priority')
    list_filter = ('criticality_level', 'priority', 'project')
    search_fields = ('site_id', 'site_name')
    filter_horizontal = ('assigned_contractors',)

@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ('site', 'status', 'structural_risk_score', 'equipment_damage_score', 'urgency_flag')
    list_editable = ('urgency_flag',)
    list_filter = ('status', 'urgency_flag')
    search_fields = ('site__site_id',)
    readonly_fields = ('structural_risk_score', 'equipment_damage_score', 'ai_repair_timeline', 'ai_resource_suggestion')

@admin.register(SitePhoto)
class SitePhotoAdmin(admin.ModelAdmin):
    list_display = ('site', 'contractor', 'category', 'status', 'ai_tags', 'uploaded_at')
    list_filter = ('status', 'category')
    search_fields = ('site__site_id', 'contractor__username', 'ai_tags')

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'client')
    list_filter = ('role',)

@admin.register(ActivityAlert)
class ActivityAlertAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'user', 'alert_type', 'site')
    list_filter = ('alert_type',)

@admin.register(SiteIssue)
class SiteIssueAdmin(admin.ModelAdmin):
    list_display = ('site', 'severity', 'is_resolved', 'created_at')
    list_filter = ('severity', 'is_resolved')

@admin.register(SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):
    list_display = ('subject', 'user', 'status', 'created_at', 'has_screenshot')
    list_editable = ('status',)
    list_filter = ('status',)
    search_fields = ('subject', 'user__username')

    def has_screenshot(self, obj):
        return bool(obj.screenshot)
    has_screenshot.boolean = True
    has_screenshot.short_description = 'Screenshot'

# 🚀 V2.0 DYNAMIC AI PROMPT CONFIGURATION
@admin.register(AIPromptSettings)
class AIPromptSettingsAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'updated_at')
    list_editable = ('is_active',)

# 🚀 PHASE 3: ENTERPRISE DRONE API KEY MANAGEMENT
@admin.register(DroneAPIKey)
class DroneAPIKeyAdmin(admin.ModelAdmin):
    list_display = ('contractor', 'key_preview', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('contractor__username', 'key')
    readonly_fields = ('key', 'created_at')
    actions = ['revoke_keys', 'activate_keys']

    def key_preview(self, obj):
        # Shows a preview of the key so the full string isn't flooding the admin table
        if obj.key:
            return f"{obj.key[:10]}...{obj.key[-4:]}"
        return "Not Generated"
    key_preview.short_description = 'Secure Key'

    @admin.action(description='🔴 Revoke selected API Keys')
    def revoke_keys(self, request, queryset):
        queryset.update(is_active=False)

    @admin.action(description='🟢 Activate selected API Keys')
    def activate_keys(self, request, queryset):
        queryset.update(is_active=True)
