from django.urls import path
from django.views.generic import TemplateView
from . import views

urlpatterns = [
    path('', views.dashboard_home, name='dashboard_home'),
    path('import-sites/', views.import_sites, name='import_sites'), 
    path('upload/', views.upload_photos, name='upload_photos'),
    path('api/drone-upload/', views.api_drone_upload, name='api_drone_upload'),
    path('upload/finish/<int:site_id>/', views.finish_upload, name='finish_upload'),
    path('sites/', views.site_visit_list, name='site_visit_list'),
    path('issues/', views.site_issues_list, name='site_issues'),
    path('issues/resolve/<int:issue_id>/', views.resolve_issue, name='resolve_issue'),
    path('issues/report/<int:site_id>/', views.report_issue, name='report_issue'),
    path('start-visit/<int:report_id>/', views.start_visit, name='start_visit'),
    path('delete-photo/<int:photo_id>/', views.delete_photo, name='delete_photo'),
    path('rework/', views.rework_log, name='rework_log'),
    path('rework/upload/<int:photo_id>/', views.rework_upload, name='rework_upload'),
    path('qa/', views.qa_hub, name='qa_hub'),
    path('qa/review/<int:site_id>/', views.qa_review, name='qa_review'),
    path('qa/approve-report/<int:report_id>/', views.approve_report, name='approve_report'),
    path('qa/decline-report/<int:report_id>/', views.decline_report, name='decline_report'),
    path('tech-writer/', views.tech_writer_hub, name='tech_writer_hub'),
    path('tech-writer/draft/<int:report_id>/', views.draft_report, name='draft_report'),
    path('logout/', views.custom_logout, name='logout'),
    path('api/alerts/', views.api_check_alerts, name='api_check_alerts'),
    path('map/', views.geographical_map_view, name='global_map'),
    path('export-csv/', views.export_performance_csv, name='export_performance_csv'),
    path('support/', views.support_page, name='support_page'),
    path('client-portal/', views.client_portal, name='client_portal'), # 🚀 NEW: Client Portal Route
    path('manifest.json', TemplateView.as_view(template_name='reports/manifest.json', content_type='application/json'), name='manifest'),
    path('sw.js', TemplateView.as_view(template_name='reports/sw.js', content_type='application/javascript'), name='sw'),
]
