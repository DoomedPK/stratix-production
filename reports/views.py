import json
import os
import csv
import io
import datetime
import time
import requests
import zipfile
import re
from io import BytesIO
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont
from google import genai
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.db.models import Q
from django.contrib.auth.models import User
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from groq import Groq
from .models import Site, SitePhoto, Report, ActivityAlert, Project, SiteIssue, Client, SupportTicket, AIPromptSettings, DroneAPIKey
from django.utils.timezone import now
from django.urls import reverse
from django.core.mail import send_mail
from django.conf import settings
from django.views.decorators.http import require_POST
from django.core.files.base import ContentFile

load_dotenv()

# --- CATEGORY MINIMUMS ---
PHOTO_MINIMUMS = {
    'Site Overview': 4,
    'Access Road': 2,
    'Tower Structure': 5,
    'Tower Base & Foundation': 14,
    'Antennas & Mounting Systems': 9,
    'Cabling & Connections': 3,
    'Equipment Shelter / Cabinets': 2,
    'Power Systems': 2,
    'Grounding & Earthing': 2,
    'Perimeter, Security & Surroundings': 5,
    'Additional Observations': 0,
}

# -------------------------------------------------------------------------
# 🚀 V2.0 AI HEATMAP ENGINE
# -------------------------------------------------------------------------
def get_site_map_status(site):
    """Calculates map colors based on Gemini AI Risk Scores first, then manual issues."""
    report = site.reports.first()
    
    # 1. AI Risk Assessment takes highest priority
    if report and report.structural_risk_score:
        score = report.structural_risk_score
        if score >= 8:
            return f'AI Critical Risk ({score}/10)', '#ef4444' # Red
        elif score >= 5:
            return f'AI Moderate Risk ({score}/10)', '#f59e0b' # Amber/Yellow
        else:
            return f'AI Low Risk ({score}/10)', '#10b981' # Green

    # 2. Fallback to manual issues if the AI hasn't analyzed it yet
    issues = site.issues.filter(is_resolved=False)
    if issues.filter(severity='Critical').exists():
        return 'Manual Critical Issue', '#ef4444' 
    elif issues.filter(severity='Major').exists():
        return 'Manual Major Issue', '#f97316' 
    elif issues.filter(severity='Minor').exists():
        return 'Manual Minor Issue', '#eab308' 
    
    if report and report.status == 'submitted':
        return 'Completed (Good Condition)', '#10b981' 
    
    return 'Pending / In Progress', '#3b82f6'

@login_required
def dashboard_home(request):
    user = request.user
    
    if user.is_superuser or (hasattr(user, 'profile') and user.profile.role in ['Admin', 'QA', 'Tech Writer']):
        base_sites = Site.objects.all()
        base_reports = Report.objects.all()
        available_projects = Project.objects.all()
    elif hasattr(user, 'profile') and user.profile.role == 'Client':
        base_sites = Site.objects.filter(project__client=user.profile.client)
        base_reports = Report.objects.filter(site__in=base_sites)
        available_projects = Project.objects.filter(client=user.profile.client)
    else:
        base_sites = Site.objects.filter(assigned_contractors=user)
        base_reports = Report.objects.filter(site__in=base_sites)
        available_projects = Project.objects.filter(sites__in=base_sites).distinct()

    selected_project_id = request.GET.get('project')
    if selected_project_id:
        sites = base_sites.filter(project_id=selected_project_id)
        reports = base_reports.filter(site__project_id=selected_project_id)
        current_project = available_projects.filter(id=selected_project_id).first()
    else:
        sites = base_sites
        reports = base_reports
        current_project = None

    # 🚀 STRATIX AI: GOD MODE NATURAL LANGUAGE FILTERS
    nl_location = request.GET.get('location')
    nl_urgency = request.GET.get('urgency')
    nl_contractor = request.GET.get('contractor')
    nl_status = request.GET.get('status')

    if nl_location:
        sites = sites.filter(location__icontains=nl_location)
        reports = reports.filter(site__in=sites)
    if nl_contractor:
        sites = sites.filter(assigned_contractors__username__icontains=nl_contractor)
        reports = reports.filter(site__in=sites)
    if nl_urgency:
        reports = reports.filter(urgency_flag__icontains=nl_urgency)
        sites = sites.filter(reports__in=reports)
    if nl_status:
        reports = reports.filter(status__icontains=nl_status)
        sites = sites.filter(reports__in=reports)

    total_sites_received = sites.count()
    total_reports_completed = reports.filter(status='submitted').count()
    total_reports_needs_completion = total_sites_received - total_reports_completed
    
    visits_completed = reports.filter(status__in=['site_data_submitted', 'qa_validation', 'engineer_review', 'submitted']).count()
    visits_remaining = total_sites_received - visits_completed
    visits_in_progress_count = reports.filter(status='visit_in_progress').count()
    reports_in_progress = reports.filter(status__in=['site_data_submitted', 'engineer_review']).count()
    
    if user.is_superuser or (hasattr(user, 'profile') and user.profile.role == 'Client'):
        pending_photos_validation = SitePhoto.objects.filter(site__in=sites, status='PENDING').count()
    else:
        pending_photos_validation = SitePhoto.objects.filter(status='PENDING').count()
        
    pending_report_validation = reports.filter(status='engineer_review').count()

    chart_data = [
        reports.filter(status='not_visited').count(),
        reports.filter(status='visit_in_progress').count(),
        reports.filter(status='site_data_submitted').count(),
        reports.filter(status='qa_validation').count(),
        reports.filter(status='engineer_review').count(),
        reports.filter(status='submitted').count(),
    ]

    status_labels = ['Not Visited', 'Visit In Progress', 'Site Data Submitted', 'QA Validation', 'Report in Progress', 'Completed/Delivered']
    status_colors = ['#64748b', '#f59e0b', '#0ea5e9', '#f97316', '#8b5cf6', '#10b981']
    status_data = [{'count': chart_data[i], 'label': status_labels[i], 'color': status_colors[i]} for i in range(6)]

    status_board = [
        {'stage': 'Pending QA Validation', 'count': pending_photos_validation, 'icon': 'fa-camera', 'color': 'warning', 'example': 'Photos uploaded by contractors, awaiting QA review.'},
        {'stage': 'Tech Drafting In Progress', 'count': reports_in_progress, 'icon': 'fa-pen-nib', 'color': 'info', 'example': 'Approved sites currently being drafted into reports.'},
        {'stage': 'Completed & Delivered', 'count': total_reports_completed, 'icon': 'fa-check-double', 'color': 'success', 'example': 'Final technical reports successfully delivered.'},
    ]

    sites_data = []
    for site in sites:
        if site.latitude and site.longitude:
            site_status, color = get_site_map_status(site) 
                    
            sites_data.append({
                'name': site.site_id,
                'site_name': site.site_name,
                'lat': float(site.latitude),
                'lng': float(site.longitude),
                'status': site_status,
                'color': color
            })

    submitted_reports = list(reports.filter(status='submitted').only('site_id', 'submitted_at'))
    sub_site_ids = [r.site_id for r in submitted_reports]
    
    all_final_alerts = ActivityAlert.objects.filter(
        site_id__in=sub_site_ids, alert_type='UPLOAD', message__icontains='Final'
    ).order_by('-timestamp').only('site_id', 'timestamp')
    
    latest_alerts_map = {}
    for alert in all_final_alerts:
        if alert.site_id not in latest_alerts_map:
            latest_alerts_map[alert.site_id] = alert.timestamp

    total_tat_days = 0
    tat_count = 0
    for r in submitted_reports:
        if r.site_id in latest_alerts_map and r.submitted_at:
            delta = latest_alerts_map[r.site_id] - r.submitted_at
            total_tat_days += delta.days
            tat_count += 1
    avg_tat = round(total_tat_days / tat_count, 1) if tat_count > 0 else 0

    trend_labels = []
    tat_trend = []
    rework_trend = []
    current_date = now().date()
    
    all_photos = list(SitePhoto.objects.filter(site__in=sites).only('site_id', 'status', 'qa_feedback', 'uploaded_at'))

    for i in range(5, -1, -1):
        target_month = (current_date.month - i - 1) % 12 + 1
        target_year = current_date.year + ((current_date.month - i - 1) // 12)
        month_label = datetime.date(target_year, target_month, 1).strftime('%b %Y')
        trend_labels.append(month_label)
        
        m_total_tat = 0
        m_tat_count = 0
        for r in submitted_reports:
            alert_time = latest_alerts_map.get(r.site_id)
            if alert_time and alert_time.year == target_year and alert_time.month == target_month and r.submitted_at:
                delta = alert_time - r.submitted_at
                m_total_tat += delta.days
                m_tat_count += 1
        tat_trend.append(round(m_total_tat / m_tat_count, 1) if m_tat_count > 0 else 0)
        
        m_photos = [p for p in all_photos if p.uploaded_at.year == target_year and p.uploaded_at.month == target_month]
        m_total_subs = len(m_photos)
        m_reworks = sum(1 for p in m_photos if p.status == 'REJECTED' or (p.qa_feedback and 'Rework' in p.qa_feedback))
        rework_trend.append(round((m_reworks / m_total_subs * 100), 1) if m_total_subs > 0 else 0)
    
    contractor_stats = []
    is_client_or_admin = user.is_superuser or (hasattr(user, 'profile') and user.profile.role in ['Admin', 'Client'])
    is_contractor = hasattr(user, 'profile') and user.profile.role == 'Contractor'
    
    if is_client_or_admin:
        contractors_to_track = list(User.objects.filter(assigned_sites__in=sites).distinct())
    elif is_contractor:
        contractors_to_track = [user]
    else:
        contractors_to_track = []

    c_ids_to_track = [c.id for c in contractors_to_track]
    
    contractor_photos = SitePhoto.objects.filter(contractor_id__in=c_ids_to_track, site__in=sites).order_by('-uploaded_at')
    
    photo_map = {c.id: [] for c in contractors_to_track}
    for p in contractor_photos:
        photo_map[p.contractor_id].append(p)

    for c in contractors_to_track:
        c_photos = photo_map.get(c.id, [])
        total_subs = len(c_photos)
        rework_photos = [p for p in c_photos if p.status == 'REJECTED' or (p.qa_feedback and 'Rework' in p.qa_feedback)]
        reworks = len(rework_photos)
        rework_rate = round((reworks / total_subs * 100), 1) if total_subs > 0 else 0
        
        recent_reworks = [p.qa_feedback for p in rework_photos if p.qa_feedback][:2]
        common_errors = recent_reworks if recent_reworks else ["No frequent errors detected."]

        contractor_stats.append({
            'id': c.id,
            'name': f"{c.first_name} {c.last_name}".strip() or c.username,
            'total_submissions': total_subs,
            'rework_rate': rework_rate,
            'common_errors': common_errors
        })

    predictive_reports = reports.exclude(predictive_risk_outlook__isnull=True).exclude(predictive_risk_outlook='').order_by('-submitted_at')[:5]

    context = {
        'user': user,
        'available_projects': available_projects,
        'current_project': current_project,
        'total_sites_received': total_sites_received,
        'total_reports_needs_completion': total_reports_needs_completion,
        'total_reports_completed': total_reports_completed,
        'visits_completed': visits_completed,
        'visits_remaining': visits_remaining,
        'visits_in_progress_count': visits_in_progress_count,
        'reports_in_progress': reports_in_progress,
        'pending_photos_validation': pending_photos_validation,
        'pending_report_validation': pending_report_validation,
        'status_data': status_data,
        'status_board': status_board,
        'sites_json': json.dumps(sites_data),
        'avg_tat': avg_tat,
        'contractor_stats': contractor_stats,
        'show_performance': is_client_or_admin or is_contractor,
        'is_client_or_admin': is_client_or_admin,
        'trend_labels': json.dumps(trend_labels),
        'tat_trend': json.dumps(tat_trend),
        'rework_trend': json.dumps(rework_trend),
        'predictive_reports': predictive_reports,
    }
    return render(request, 'reports/dashboard.html', context)


@login_required
def import_sites(request):
    user = request.user
    if not (user.is_superuser or (hasattr(user, 'profile') and user.profile.role == 'Admin')):
        return redirect('dashboard_home')

    if request.method == 'POST':
        file = request.FILES.get('import_file')
        if not file:
            messages.error(request, "Please select a file to upload.")
            return redirect('import_sites')

        if not file.name.endswith('.csv'):
            messages.error(request, "Invalid file format. Please ensure you saved your Excel file as a .csv")
            return redirect('import_sites')

        try:
            decoded_file = file.read().decode('utf-8-sig')
            io_string = io.StringIO(decoded_file)
            reader = csv.DictReader(io_string)
            
            success_count = 0
            error_count = 0
            
            for row in reader:
                clean_row = {k.strip().lower(): v.strip() for k, v in row.items() if k}
                site_id = clean_row.get('site_id')
                site_name = clean_row.get('site_name', 'Unnamed Site')
                project_name = clean_row.get('project')
                location = clean_row.get('location', '')
                lat_val = clean_row.get('latitude')
                lng_val = clean_row.get('longitude')
                height_val = clean_row.get('site_height')
                priority = clean_row.get('priority', 'Medium')

                if not site_id or not project_name:
                    error_count += 1
                    continue
                    
                latitude = float(lat_val) if lat_val else None
                longitude = float(lng_val) if lng_val else None
                height_in_meters = float(height_val) if height_val else None
                
                default_client, _ = Client.objects.get_or_create(name="Unassigned Client (Auto-Imported)")
                project, p_created = Project.objects.get_or_create(name=project_name, defaults={'client': default_client})
                
                site, s_created = Site.objects.update_or_create(
                    site_id=site_id,
                    defaults={
                        'site_name': site_name, 
                        'project': project, 
                        'location': location, 
                        'latitude': latitude, 
                        'longitude': longitude, 
                        'height_in_meters': height_in_meters,
                        'priority': priority
                    }
                )
                
                if s_created:
                    Report.objects.create(site=site, status='not_visited')
                    ActivityAlert.objects.create(message=f"Bulk imported site {site_id}.", user=user, site=site, alert_type='UPLOAD')
                    
                success_count += 1
            
            messages.success(request, f"Successfully imported/updated {success_count} sites! {error_count} rows skipped.")
            return redirect('site_visit_list')
            
        except Exception as e:
            messages.error(request, f"Error reading file. Ensure it matches the template format. ({str(e)})")
            return redirect('import_sites')

    return render(request, 'reports/import_sites.html')


@login_required
def site_visit_list(request):
    user = request.user
    if user.is_superuser or (hasattr(user, 'profile') and user.profile.role in ['Admin', 'QA', 'Tech Writer']):
        reports_list = Report.objects.all()
        projects = Project.objects.all()
    elif hasattr(user, 'profile') and user.profile.role == 'Client':
        reports_list = Report.objects.filter(site__project__client=user.profile.client)
        projects = Project.objects.filter(client=user.profile.client)
    else:
        reports_list = Report.objects.filter(site__assigned_contractors=user)
        projects = Project.objects.filter(sites__assigned_contractors=user).distinct()

    return render(request, 'reports/site_list.html', {'reports': reports_list, 'projects': projects})

@login_required
def report_issue(request, site_id):
    user = request.user
    if not (user.is_superuser or (hasattr(user, 'profile') and user.profile.role in ['Admin', 'QA'])):
        return redirect('site_visit_list')

    if request.method == 'POST':
        site = get_object_or_404(Site, id=site_id)
        severity = request.POST.get('severity', 'Minor')
        description = request.POST.get('description', 'No description provided.')
        SiteIssue.objects.create(site=site, reported_by=request.user, severity=severity, description=description)
        ActivityAlert.objects.create(message=f"{severity} issue logged for this site.", user=request.user, site=site, alert_type='REWORK')
        messages.success(request, f"Issue logged for Site {site.site_id}.")
        
    referer = request.META.get('HTTP_REFERER')
    if referer:
        return redirect(referer)
    return redirect('site_visit_list')

@login_required
def site_issues_list(request):
    user = request.user
    if user.is_superuser or (hasattr(user, 'profile') and user.profile.role in ['Admin', 'QA', 'Tech Writer']):
        issues = SiteIssue.objects.filter(is_resolved=False).order_by('-created_at')
        projects = Project.objects.filter(sites__issues__is_resolved=False).distinct()
    elif hasattr(user, 'profile') and user.profile.role == 'Client':
        issues = SiteIssue.objects.filter(site__project__client=user.profile.client, is_resolved=False).order_by('-created_at')
        projects = Project.objects.filter(client=user.profile.client, sites__issues__is_resolved=False).distinct()
    else:
        issues = SiteIssue.objects.filter(site__assigned_contractors=user, is_resolved=False).order_by('-created_at')
        projects = Project.objects.filter(sites__assigned_contractors=user, sites__issues__is_resolved=False).distinct()

    return render(request, 'reports/site_issues.html', {'issues': issues, 'projects': projects})


@login_required
def upload_photos(request):
    user = request.user
    
    site_id = request.GET.get('site_id') or request.POST.get('site_id')
    selected_site = get_object_or_404(Site, id=site_id) if site_id else None

    if request.method == 'POST' and selected_site:
        category = request.POST.get('category')
        notes = request.POST.get('contractor_notes')
        images = request.FILES.getlist('site_images')
        
        for image in images:
            SitePhoto.objects.create(
                site=selected_site, contractor=user, image=image, status='PENDING',
                category=category, contractor_notes=notes
            )
        messages.success(request, f"Uploaded {len(images)} photos to '{category}'.")
        return redirect(f"{reverse('upload_photos')}?site_id={selected_site.id}")

    if user.is_superuser or (hasattr(user, 'profile') and user.profile.role in ['Admin', 'QA']):
        sites = Site.objects.filter(reports__status='visit_in_progress').distinct()
    else:
        sites = Site.objects.filter(assigned_contractors=user, reports__status='visit_in_progress').distinct()

    uploaded_photos = SitePhoto.objects.filter(site=selected_site, contractor=user).order_by('-uploaded_at') if selected_site else None

    return render(request, 'reports/upload_photo.html', {
        'sites': sites, 
        'selected_site': selected_site, 
        'uploaded_photos': uploaded_photos,
        'minimums': PHOTO_MINIMUMS
    })

# -------------------------------------------------------------------------
# 🚀 PHASE 3: AI VISION ENGINE (PREDICTIVE & BOUNDING BOXES)
# -------------------------------------------------------------------------
@login_required
def finish_upload(request, site_id):
    site = get_object_or_404(Site, id=site_id)
    if request.method == 'POST':
        report = site.reports.first()
        
        if request.POST.get('drone_3d_link'):
            report.drone_3d_model_link = request.POST.get('drone_3d_link')
            report.save()
        
        if site.project.require_photo_minimums:
            missing = []
            for cat, min_count in PHOTO_MINIMUMS.items():
                if min_count > 0:
                    count = SitePhoto.objects.filter(site=site, category=cat).count()
                    if count < min_count:
                        missing.append(f"{cat} (needs {min_count - count} more)")
            
            if missing:
                messages.error(request, "Cannot finish upload! Missing required photos: " + ", ".join(missing))
                return redirect(f"{reverse('upload_photos')}?site_id={site.id}")
                
        report = site.reports.first()
        if report and report.status == 'visit_in_progress':
            try:
                client = genai.Client(api_key=settings.GEMINI_API_KEY)
                # 🚀 NEW: Grab up to 100 photos, but order them by Category so the AI sees the whole site
                recent_photos = list(SitePhoto.objects.filter(site=site).order_by('category', '-uploaded_at')[:100])
                
                active_prompt = AIPromptSettings.objects.filter(is_active=True).first()
                base_instruction = active_prompt.prompt_text if active_prompt and active_prompt.prompt_text else "Analyze these photos."
                
                past_issues = site.issues.filter(is_resolved=False)
                issues_text = "; ".join([f"{i.severity}: {i.description}" for i in past_issues]) if past_issues else "No prior unresolved issues."
                notes_list = [f"- {p.category}: {p.contractor_notes}" for p in recent_photos if p.contractor_notes]
                notes_text = "\n".join(notes_list) if notes_list else "No contractor field notes provided."

                dynamic_context = f"""
                --- LIVE DATABASE INPUT DATA ---
                Location: {site.location}
                Coordinates: {site.latitude}, {site.longitude}
                Site Height: {site.height_in_meters} meters
                Criticality Level: {site.criticality_level}
                Previous Inspection/Issues Data: {issues_text}
                CONTRACTOR FIELD NOTES: {notes_text}
                --------------------------------
                """

                prompt_content = [base_instruction, dynamic_context]
                pil_images = []

                for p in recent_photos:
                    if p.image:
                        img_url = request.build_absolute_uri(p.image.url) if p.image.url.startswith('/') else p.image.url
                        response = requests.get(img_url, timeout=10)
                        if response.status_code == 200:
                            img = Image.open(BytesIO(response.content)).convert("RGB")
                            # 🚀 NEW: Aggressively compress to 800x800 to allow 100+ photos without timeout
                            img.thumbnail((800, 800)) 
                            prompt_content.append(img)
                            pil_images.append((p, img)) # Keep track of which image is which

                if len(pil_images) > 0:
                    ai_response = client.models.generate_content(
                        model='gemini-2.5-flash',
                        contents=prompt_content
                    )
                    ai_text = ai_response.text.strip()
                    # 🚀 V2.0 CRASH-PROOF JSON EXTRACTOR
                    json_match = re.search(r'\{.*\}', ai_text, re.DOTALL)
                    if json_match:
                        ai_text = json_match.group(0)

                    try:
                        # Standard JSON parse
                        ai_data = json.loads(ai_text.strip())
                    except json.JSONDecodeError:
                        # If Gemini messes up the quotation marks, we use AST as a bulletproof fallback!
                        import ast
                        # Convert unescaped double quotes inside strings to single quotes to save the dictionary
                        fixed_text = re.sub(r'(?<!\\)"(?!:|,|\s*\}|\s*\])', "'", ai_text)
                        try:
                            ai_data = ast.literal_eval(fixed_text.strip())
                        except Exception as e2:
                            print(f"AST Fallback Failed: {e2}")
                            ai_data = {} # Fail gracefully

                    report.structural_risk_score = ai_data.get('structural_risk_score')
                    report.equipment_damage_score = ai_data.get('equipment_damage_score')
                    report.urgency_flag = ai_data.get('urgency_flag', 'Low')
                    report.ai_repair_timeline = ai_data.get('ai_repair_timeline')
                    report.ai_resource_suggestion = ai_data.get('tobby_full_report', ai_data.get('ai_resource_suggestion', 'N/A'))
                    report.client_executive_summary = ai_data.get('client_executive_summary', '')
                    report.historical_trend_analysis = ai_data.get('historical_trend_analysis', '')
                    report.category_damage_breakdown = ai_data.get('category_damage_breakdown', '')
                    
                    report.predictive_risk_outlook = ai_data.get('predictive_risk_outlook', '')
                    
                    boxes_data = ai_data.get('annotated_damages', [])
                    
                    for index, (photo_obj, pil_img) in enumerate(pil_images):
                        photo_obj.ai_tags = ai_data.get('ai_tags', '')
                        
                        # Find boxes for this specific image index
                        photo_boxes = [b for b in boxes_data if b.get('photo_index') == index]
                        if photo_boxes:
                            draw = ImageDraw.Draw(pil_img)
                            width, height = pil_img.size
                            for box in photo_boxes:
                                coords = box.get('box_2d', [0,0,0,0])
                                if len(coords) == 4:
                                    ymin, xmin, ymax, xmax = coords
                                    left = (xmin / 1000) * width
                                    top = (ymin / 1000) * height
                                    right = (xmax / 1000) * width
                                    bottom = (ymax / 1000) * height
                                    
                                    draw.rectangle([left, top, right, bottom], outline="red", width=5)
                                    label = box.get('issue', 'Damage')
                                    draw.text((left, top - 15), label, fill="red")
                            
                            buffer = BytesIO()
                            pil_img.save(buffer, format='JPEG', quality=85)
                            file_name = f"annotated_{photo_obj.id}.jpg"
                            photo_obj.annotated_image.save(file_name, ContentFile(buffer.getvalue()), save=False)
                            
                        photo_obj.save()

                    if report.urgency_flag in ['Medium', 'High']:
                        severity_level = 'Critical' if report.urgency_flag == 'High' else 'Major'
                        ai_issue_desc = f"[AI AUTO-DETECTED] Stratix Vision Engine flagged anomalies.\nStructural Risk score: {report.structural_risk_score}/10\nTags: {ai_data.get('ai_tags', 'None')}\nRecommended Timeline for Restoration Fixes: {report.ai_repair_timeline}"
                        if not SiteIssue.objects.filter(site=site, description__contains="[AI AUTO-DETECTED]", is_resolved=False).exists():
                            SiteIssue.objects.create(site=site, reported_by=None, severity=severity_level, description=ai_issue_desc)
                        
            except Exception as e:
                print(f"AI Engine Error: {str(e)}")

            report.status = 'qa_validation' 
            report.save()
            ActivityAlert.objects.create(message=f"Contractor finished uploading. AI Analysis complete.", user=request.user, site=site, alert_type='UPLOAD')
            messages.success(request, "Uploads completed and sent to QA for validation!")
    
    return redirect('site_visit_list')

@csrf_exempt
def api_drone_upload(request):
    if request.method == 'POST':
        provided_key = request.POST.get('api_key')
        api_record = DroneAPIKey.objects.filter(key=provided_key, is_active=True).first()
        
        if not api_record:
            return JsonResponse({'error': 'Unauthorized or Revoked API Key'}, status=401)
            
        site_id_val = request.POST.get('site_id')
        category = request.POST.get('category', 'Tower Structure')
        image_file = request.FILES.get('image')
        
        if not site_id_val or not image_file:
            return JsonResponse({'error': 'Missing site_id or image'}, status=400)
            
        site = get_object_or_404(Site, site_id=site_id_val)
        
        SitePhoto.objects.create(
            site=site, 
            contractor=api_record.contractor,
            image=image_file, 
            category=category, 
            status='PENDING', 
            is_drone_capture=True,
            contractor_notes="AUTONOMOUS DRONE CAPTURE"
        )
        return JsonResponse({'success': True, 'message': f'Drone image saved to {site.site_id}'})
    
    return JsonResponse({'error': 'POST required'}, status=405)

@login_required
@require_POST
def start_visit(request, report_id):
    report = get_object_or_404(Report, id=report_id)
    report.status = 'visit_in_progress'
    report.save()
    ActivityAlert.objects.create(message=f"Contractor has arrived on site.", user=request.user, site=report.site, alert_type='CHECK_IN')
    return redirect(f"{reverse('upload_photos')}?site_id={report.site.id}")

@login_required
def rework_log(request):
    user = request.user
    if user.is_superuser or (hasattr(user, 'profile') and user.profile.role in ['Admin', 'QA']):
        reworks = SitePhoto.objects.filter(status='REJECTED').order_by('-uploaded_at')
    elif hasattr(user, 'profile') and user.profile.role == 'Client':
        reworks = SitePhoto.objects.filter(site__project__client=user.profile.client, status='REJECTED').order_by('-uploaded_at')
    else:
        reworks = SitePhoto.objects.filter(contractor=user, status='REJECTED').order_by('-uploaded_at')
    return render(request, 'reports/rework_log.html', {'reworks': reworks})

@login_required
def rework_upload(request, photo_id):
    photo = get_object_or_404(SitePhoto, id=photo_id, status='REJECTED')
    if not request.user.is_superuser and request.user != photo.contractor:
        return redirect('rework_log')

    if request.method == 'POST':
        new_image = request.FILES.get('replacement_image')
        notes = request.POST.get('contractor_notes', '')
        if new_image:
            photo.image = new_image
            photo.status = 'PENDING'
            photo.contractor_notes = notes
            photo.qa_feedback = f"[Rework Submitted] " + (photo.qa_feedback or "")
            photo.save()
            ActivityAlert.objects.create(message=f"Contractor uploaded a fix.", user=request.user, site=photo.site, alert_type='UPLOAD')
            return redirect('rework_log')
    return render(request, 'reports/rework_upload.html', {'photo': photo})

@login_required
def qa_hub(request):
    user = request.user
    if not (user.is_superuser or (hasattr(user, 'profile') and user.profile.role in ['Admin', 'QA'])):
        return redirect('dashboard_home')
        
    sites_needing_review = Site.objects.filter(photos__status='PENDING').distinct()
    drafted_reports = Report.objects.filter(status='engineer_review')
    
    return render(request, 'reports/qa_hub.html', {'sites': sites_needing_review, 'drafted_reports': drafted_reports})

@login_required
def qa_review(request, site_id):
    user = request.user
    if not (user.is_superuser or (hasattr(user, 'profile') and user.profile.role in ['Admin', 'QA'])):
        return redirect('dashboard_home')

    site = get_object_or_404(Site, id=site_id)
    pending_photos = SitePhoto.objects.filter(site=site, status='PENDING').order_by('category')

    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'bulk_approve':
            photo_ids = request.POST.getlist('photo_ids')
            if photo_ids:
                SitePhoto.objects.filter(id__in=photo_ids, site=site).update(status='APPROVED')
                messages.success(request, f"Successfully approved {len(photo_ids)} photos.")
            else:
                messages.warning(request, "No photos selected.")
                
        elif action == 'bulk_reject':
            photo_ids = request.POST.getlist('photo_ids')
            if photo_ids:
                bulk_feedback = request.POST.get('bulk_feedback', 'Bulk Rejected by QA')
                photos_to_reject = SitePhoto.objects.filter(id__in=photo_ids, site=site)
                for p in photos_to_reject:
                    p.status = 'REJECTED'
                    p.qa_feedback = f"[Reworked] {bulk_feedback}" if 'Rework' in (p.qa_feedback or "") else bulk_feedback
                    p.save()
                ActivityAlert.objects.create(message=f"QA bulk-rejected {len(photo_ids)} photos for rework.", user=request.user, site=site, alert_type='REWORK')
                messages.warning(request, f"Bulk rejected {len(photo_ids)} photos.")
            else:
                messages.warning(request, "No photos selected.")
                
        elif action and action.startswith('approve_'):
            photo_id = action.split('_')[1]
            photo = get_object_or_404(SitePhoto, id=photo_id, site=site)
            photo.status = 'APPROVED'
            photo.save()
            
        elif action and action.startswith('reject_'):
            photo_id = action.split('_')[1]
            feedback = request.POST.get(f'feedback_{photo_id}', '')
            photo = get_object_or_404(SitePhoto, id=photo_id, site=site)
            photo.status = 'REJECTED'
            photo.qa_feedback = f"[Reworked] {feedback}" if 'Rework' in (photo.qa_feedback or "") else feedback
            photo.save()
            ActivityAlert.objects.create(message="QA rejected a photo.", user=request.user, site=site, alert_type='REWORK')

        if SitePhoto.objects.filter(site=site, status__in=['PENDING', 'REJECTED']).count() == 0 and SitePhoto.objects.filter(site=site).count() > 0:
            report = Report.objects.filter(site=site).first()
            if report and report.status == 'qa_validation':
                report.status = 'site_data_submitted'
                report.save()
                ActivityAlert.objects.create(message="Site Validated. Ready for technical writing.", user=request.user, site=site, alert_type='UPLOAD')
            return redirect('qa_hub')
            
        return redirect('qa_review', site_id=site.id)
        
    return render(request, 'reports/qa_review.html', {'site': site, 'photos': pending_photos})

@login_required
def approve_report(request, report_id):
    user = request.user
    if not (user.is_superuser or (hasattr(user, 'profile') and user.profile.role in ['Admin', 'QA'])):
        return redirect('dashboard_home')
        
    report = get_object_or_404(Report, id=report_id)
    if request.method == 'POST':
        report.status = 'submitted'
        report.save()
        ActivityAlert.objects.create(message="Final Technical Report Approved and Sent to Client.", user=request.user, site=report.site, alert_type='UPLOAD')
        messages.success(request, "Report Approved and Delivered!")
    return redirect('qa_hub')

@login_required
def decline_report(request, report_id):
    user = request.user
    if not (user.is_superuser or (hasattr(user, 'profile') and user.profile.role in ['Admin', 'QA'])):
        return redirect('dashboard_home')
        
    report = get_object_or_404(Report, id=report_id)
    if request.method == 'POST':
        reason = request.POST.get('reason', 'No reason provided.')
        report.status = 'site_data_submitted' 
        report.final_document = None 
        report.comments = f"DECLINED BY QA: {reason} | Previous Notes: {report.comments}"
        report.save()
        ActivityAlert.objects.create(message="QA declined the drafted report.", user=user, site=report.site, alert_type='REWORK')
        messages.warning(request, "Report declined and sent back to Technical Writer.")
    return redirect('qa_hub')

@login_required
def tech_writer_hub(request):
    user = request.user
    if not (user.is_superuser or (hasattr(user, 'profile') and user.profile.role in ['Admin', 'Tech Writer', 'QA'])):
        return redirect('dashboard_home')
        
    reports_to_draft = Report.objects.filter(status='site_data_submitted')
    return render(request, 'reports/tech_writer_hub.html', {'reports': reports_to_draft})

@login_required
def draft_report(request, report_id):
    user = request.user
    if not (user.is_superuser or (hasattr(user, 'profile') and user.profile.role in ['Admin', 'Tech Writer', 'QA'])):
        return redirect('dashboard_home')

    report = get_object_or_404(Report, id=report_id)
    approved_photos = SitePhoto.objects.filter(site=report.site, status='APPROVED').order_by('category')

    if request.method == 'POST':
        final_pdf = request.FILES.get('final_document')
        comments = request.POST.get('comments', '')
        
        report.client_executive_summary = request.POST.get('client_executive_summary', report.client_executive_summary)
        report.category_damage_breakdown = request.POST.get('category_damage_breakdown', report.category_damage_breakdown)
        report.historical_trend_analysis = request.POST.get('historical_trend_analysis', report.historical_trend_analysis)
        report.predictive_risk_outlook = request.POST.get('predictive_risk_outlook', report.predictive_risk_outlook)
        report.drone_3d_model_link = request.POST.get('drone_3d_model_link', report.drone_3d_model_link)
        
        if final_pdf:
            report.final_document = final_pdf
            
        report.comments = comments
        report.status = 'engineer_review' 
        report.save() 
        
        ActivityAlert.objects.create(message="Draft Report submitted for QA final approval.", user=request.user, site=report.site, alert_type='UPLOAD')
        messages.success(request, "Draft sent to QA!")
        return redirect('tech_writer_hub')

    return render(request, 'reports/draft_report.html', {'report': report, 'photos': approved_photos})

@login_required
def custom_logout(request):
    logout(request)
    return redirect('login')

@login_required
def api_check_alerts(request):
    current_time = time.time()
    last_request = request.session.get('last_api_request', 0)
    if current_time - last_request < 2:  
        return JsonResponse({'new_alerts': [], 'error': 'Rate limit exceeded'}, status=429)
    request.session['last_api_request'] = current_time

    user = request.user
    last_check_str = request.session.get('last_alert_check')
    
    if user.is_superuser or (hasattr(user, 'profile') and user.profile.role in ['Admin', 'QA']):
        alerts = ActivityAlert.objects.all()
    elif hasattr(user, 'profile') and user.profile.role == 'Client':
        base_sites = Site.objects.filter(project__client=user.profile.client)
        alerts = ActivityAlert.objects.filter(site__in=base_sites, alert_type='UPLOAD', message__icontains='Final')
    elif hasattr(user, 'profile') and user.profile.role == 'Tech Writer':
        alerts = ActivityAlert.objects.filter(message__icontains='technical writing')
    else:
        base_sites = Site.objects.filter(assigned_contractors=user)
        alerts = ActivityAlert.objects.filter(site__in=base_sites)

    if last_check_str:
        last_check = datetime.datetime.fromisoformat(last_check_str)
        new_alerts = alerts.filter(timestamp__gt=last_check).order_by('-timestamp')
    else:
        new_alerts = []
    request.session['last_alert_check'] = now().isoformat()
    alerts_data = [{'message': a.message, 'site': a.site.site_id, 'type': a.alert_type} for a in new_alerts]
    return JsonResponse({'new_alerts': alerts_data})

@login_required
def geographical_map_view(request):
    user = request.user
    if user.is_superuser or (hasattr(user, 'profile') and user.profile.role in ['Admin', 'QA', 'Tech Writer']):
        sites = Site.objects.all()
    elif hasattr(user, 'profile') and user.profile.role == 'Client':
        sites = Site.objects.filter(project__client=user.profile.client)
    else:
        sites = Site.objects.filter(assigned_contractors=user)
    
    sites_data = []
    for site in sites:
        if site.latitude and site.longitude:
            site_status, color = get_site_map_status(site)
                    
            sites_data.append({
                'name': site.site_id,
                'site_name': site.site_name,
                'lat': float(site.latitude),
                'lng': float(site.longitude),
                'status': site_status,
                'color': color
            })
            
    return render(request, 'reports/geographical_map_view.html', {'sites_json': json.dumps(sites_data)})

@login_required
def export_performance_csv(request):
    user = request.user
    if not (user.is_superuser or (hasattr(user, 'profile') and user.profile.role in ['Admin', 'Client'])):
        return redirect('dashboard_home')
    
    if hasattr(user, 'profile') and user.profile.role == 'Client':
        sites = Site.objects.filter(project__client=user.profile.client)
    else:
        sites = Site.objects.all()
        
    selected_project_id = request.GET.get('project')
    if selected_project_id:
        sites = sites.filter(project_id=selected_project_id)
        
    contractors = User.objects.filter(assigned_sites__in=sites).distinct()
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="Contractor_Performance_Export.csv"'
    writer = csv.writer(response)
    writer.writerow(['Contractor Name', 'Total Submissions', 'Reworks', 'Rework Rate (%)', 'Common Errors'])
    
    for c in contractors:
        c_photos = SitePhoto.objects.filter(contractor=c, site__in=sites)
        total_subs = c_photos.count()
        reworks = c_photos.filter(Q(status='REJECTED') | Q(qa_feedback__icontains='Rework')).count()
        rework_rate = round((reworks / total_subs * 100), 1) if total_subs > 0 else 0
        recent_reworks = c_photos.filter(Q(status='REJECTED') | Q(qa_feedback__icontains='Rework')).exclude(qa_feedback__isnull=True).exclude(qa_feedback='').order_by('-uploaded_at')[:2]
        errors = " | ".join([p.qa_feedback for p in recent_reworks]) if recent_reworks else "None"
        writer.writerow([f"{c.first_name} {c.last_name}".strip() or c.username, total_subs, reworks, rework_rate, errors])
    return response

@login_required
def support_page(request):
    if request.method == 'POST':
        ticket_subject = request.POST.get('subject', 'General Support')
        description = request.POST.get('description', 'No description provided.')
        screenshot = request.FILES.get('screenshot')
        
        ticket = SupportTicket.objects.create(
            user=request.user,
            subject=ticket_subject,
            description=description,
            screenshot=screenshot,
            status='Pending'
        )
        
        ActivityAlert.objects.create(
            message=f"New Support Ticket #{ticket.id} Submitted: {ticket_subject}", 
            user=request.user, 
            site=Site.objects.first(), 
            alert_type='REWORK'
        )

        try:
            screenshot_status = "Yes (Attached in Admin Panel)" if screenshot else "No image attached"
            email_message = f"""
New Support Ticket #{ticket.id}

Submitted By: {request.user.get_full_name()} ({request.user.username})
Role: {request.user.profile.get_role_display()}

Subject: {ticket_subject}

Description:
{description}

Screenshot Provided: {screenshot_status}

---
Please log into the Stratix Command Center admin panel to view and resolve this ticket.
"""
            send_mail(
                subject=f"[STRATIX ALERT] Support Ticket #{ticket.id}: {ticket_subject}",
                message=email_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=['clientrelations@stratixjm.com'],
                fail_silently=True,
            )
        except Exception as e:
            print(f"SMTP Error: Could not send email. {str(e)}")

        messages.success(request, "Your support ticket has been prioritized and sent to the Support Team. We will contact you shortly!")
        return redirect('dashboard_home')
        
    return render(request, 'reports/support.html')

@login_required
def client_portal(request):
    user = request.user
    if not (user.is_superuser or (hasattr(user, 'profile') and user.profile.role in ['Admin', 'Client'])):
        return redirect('dashboard_home')
        
    if hasattr(user, 'profile') and user.profile.role == 'Client':
        completed_reports = Report.objects.filter(site__project__client=user.profile.client, status='submitted').order_by('-submitted_at')
        projects = Project.objects.filter(client=user.profile.client)
    else:
        completed_reports = Report.objects.filter(status='submitted').order_by('-submitted_at')
        projects = Project.objects.all()

    selected_project_id = request.GET.get('project')
    if selected_project_id:
        completed_reports = completed_reports.filter(site__project_id=selected_project_id)
        
    return render(request, 'reports/client_portal.html', {
        'reports': completed_reports, 
        'projects': projects,
        'current_project': selected_project_id
    })

@login_required
def delete_photo(request, photo_id):
    if request.method == 'POST':
        photo = get_object_or_404(SitePhoto, id=photo_id, contractor=request.user)
        site_id = photo.site.id
        photo.delete()
        messages.success(request, "Photo successfully removed from the upload queue.")
        return redirect(f'/upload-photos/?site_id={site_id}')
    return redirect('dashboard_home')

@login_required
@require_POST
def resolve_issue(request, issue_id):
    user = request.user
    # Only allow Admins and QA to resolve issues
    if not (user.is_superuser or (hasattr(user, 'profile') and user.profile.role in ['Admin', 'QA'])):
        return redirect('dashboard_home')
        
    issue = get_object_or_404(SiteIssue, id=issue_id)
    issue.is_resolved = True
    issue.save()
    
    # Log the action
    ActivityAlert.objects.create(
        message=f"Site Issue Resolved: {issue.site.site_id}", 
        user=request.user, 
        site=issue.site, 
        alert_type='UPLOAD'
    )
    messages.success(request, f"Issue for {issue.site.site_id} has been marked as completely fixed!")
    
    return redirect('site_issues_list')

# -----------------------------------------------------------------------------
# STRATIX AI: AUTOPILOT (TECH WRITER HUB)
# -----------------------------------------------------------------------------
@csrf_exempt
@login_required
def groq_rewrite(request):
    if request.method == 'POST':
        if request.user.profile.role not in ['Admin', 'QA', 'Tech Writer'] and not request.user.is_superuser:
            return JsonResponse({'error': 'Unauthorized'}, status=403)

        try:
            data = json.loads(request.body)
            original_text = data.get('text', '')
            style = data.get('style', 'professional')

            if not original_text:
                return JsonResponse({'error': 'No text provided'}, status=400)

            system_prompts = {
                'professional': "You are an expert Telecommunications Structural Engineer. Rewrite the following inspection text to sound highly professional, corporate, and polished. Fix any grammatical errors. DO NOT add new facts or guess data. Return ONLY the rewritten text.",
                'concise': "You are an expert Telecommunications Executive. Rewrite the following inspection text to be extremely concise, bullet-pointed if necessary, and straight to the point. Remove fluff. DO NOT add new facts. Return ONLY the rewritten text.",
                'urgent': "You are an Emergency Telecommunications Dispatcher. Rewrite the following inspection text to highlight severe urgency and critical risk. Use strong, assertive language indicating immediate action is required. DO NOT add new facts. Return ONLY the rewritten text."
            }

            selected_prompt = system_prompts.get(style, system_prompts['professional'])

            load_dotenv()
            client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
            
            chat_completion = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": selected_prompt},
                    {"role": "user", "content": f"Rewrite this text:\n\n{original_text}"}
                ],
                model="llama-3.3-70b-versatile",
                temperature=0.3,
            )

            return JsonResponse({'rewritten_text': chat_completion.choices[0].message.content.strip()})

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Invalid request method'}, status=405)

# -----------------------------------------------------------------------------
# STRATIX AI: CONSULTANT CHAT WITH PDF VISION (CLIENT PORTAL)
# -----------------------------------------------------------------------------
@csrf_exempt
@login_required
def report_chat(request):
    """
    Allows clients to ask questions about a specific report.
    Acts as an elite telecommunications consultant, utilizing both DB data and PDF text.
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            report_id = data.get('report_id')
            user_message = data.get('message')

            if not report_id or not user_message:
                return JsonResponse({'error': 'Missing report ID or message'}, status=400)

            report = get_object_or_404(Report, id=report_id)

            if hasattr(request.user, 'profile') and request.user.profile.role == 'Client':
                if report.site.project.client != request.user.profile.client:
                    return JsonResponse({'error': 'Unauthorized Access'}, status=403)

            # --- Extract Text from the Uploaded PDF (if it exists) ---
            pdf_text = ""
            if report.final_document:
                try:
                    import PyPDF2
                    pdf_file = report.final_document.file
                    pdf_reader = PyPDF2.PdfReader(pdf_file)
                    for page in pdf_reader.pages:
                        text = page.extract_text()
                        if text:
                            pdf_text += text + "\n"
                except Exception as e:
                    pdf_text = f"[PDF Vision could not extract text automatically. Error: {str(e)}]"
            else:
                pdf_text = "[No PDF attached to this report yet.]"

            # --- Build the Database Fact Sheet ---
            db_context = f"""
            Site ID: {report.site.site_id}
            Site Name: {report.site.site_name}
            Structural Risk Score: {report.structural_risk_score}/10
            Urgency Flag: {report.urgency_flag}
            Recommended Repair Timeline: {report.ai_repair_timeline}
            
            Executive Summary:
            {report.client_executive_summary}
            
            Damage Breakdown:
            {report.category_damage_breakdown}
            
            Predictive Risk Outlook:
            {report.predictive_risk_outlook}
            """

            # --- The New "Concise Consultant Mode" Prompt ---
            system_prompt = f"""You are 'Stratix AI', an elite telecommunications infrastructure consultant advising a client.
Your goal is to give the client clear, actionable, and highly concise answers about their site report.

Below is the raw database data for the report, followed by the raw extracted text from the final PDF document (if available).

--- START OF DATABASE FACT SHEET ---
{db_context}

--- START OF PDF DOCUMENT TEXT ---
{pdf_text}
--- END OF DATA ---

INSTRUCTIONS FOR YOU:
1. Base all your factual answers entirely on the data provided above.
2. DO NOT just blindly repeat the text. Act as a senior expert consultant interpreting the data.
3. If the client asks "how to fix this" or "what teams to send", use your general knowledge to suggest specific trades (e.g., "You need a structural welding crew"), but keep the explanation BRIEF.
4. Be empathetic and professional, but EXTREMELY CONCISE. Do not write long essays. Use bullet points if it helps with readability. Answer the exact question asked without unnecessary fluff or rambling.
"""

            # Connect to Groq
            load_dotenv()
            client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
            
            chat_completion = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                model="llama-3.3-70b-versatile",
                temperature=0.4, 
            )

            return JsonResponse({'response': chat_completion.choices[0].message.content})

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Invalid request method'}, status=405)

# -----------------------------------------------------------------------------
# STRATIX AI: GOD MODE DASHBOARD FILTER (NATURAL LANGUAGE TO JSON)
# -----------------------------------------------------------------------------
@csrf_exempt
@login_required
def nl_filter_translator(request):
    if request.method == 'POST':
        # Security: Only Admins and QA can use the God Mode search
        if not (request.user.is_superuser or (hasattr(request.user, 'profile') and request.user.profile.role in ['Admin', 'QA'])):
            return JsonResponse({'error': 'Unauthorized'}, status=403)

        try:
            data = json.loads(request.body)
            query = data.get('query', '')

            if not query:
                return JsonResponse({'error': 'No query provided'}, status=400)

            system_prompt = """You are a backend database translator. 
Convert the user's natural language search into a strict JSON object to filter a telecom dashboard. 
Extract the intent and return a JSON object with ONLY these exact keys (use null if the user did not mention it):
- "location": (string, e.g., "Kingston", "St. Ann")
- "urgency": (string, exactly "High", "Medium", or "Low")
- "contractor": (string, name of the contractor/person)
- "status": (string, exactly "not_visited", "visit_in_progress", "site_data_submitted", "qa_validation", "engineer_review", "submitted")

Do not add any other text. Return ONLY the JSON object."""

            load_dotenv()
            client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
            
            chat_completion = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": query}
                ],
                model="llama-3.3-70b-versatile",
                temperature=0, 
                response_format={"type": "json_object"} 
            )

            result = json.loads(chat_completion.choices[0].message.content)
            return JsonResponse(result)

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Invalid request method'}, status=405)

# -----------------------------------------------------------------------------
# USER ONBOARDING TUTORIAL TRACKER
# -----------------------------------------------------------------------------
@csrf_exempt
@login_required
def mark_tutorial_seen(request):
    if request.method == 'POST':
        profile = request.user.profile
        profile.has_seen_tutorial = True
        profile.save()
        return JsonResponse({'status': 'success'})
    return JsonResponse({'error': 'Invalid request method'}, status=405)


@login_required
def download_site_photos_zip(request, site_id):
    # Only let Admins, QA, or Tech Writers bulk download
    if not (request.user.is_superuser or (hasattr(request.user, 'profile') and request.user.profile.role in ['Admin', 'QA', 'Tech Writer'])):
        return redirect('dashboard_home')
        
    site = get_object_or_404(Site, id=site_id)
    # Grab all photos for the site
    photos = SitePhoto.objects.filter(site=site)
    
    # Create an in-memory ZIP file
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for photo in photos:
            if photo.image:
                try:
                    # Read the image from Supabase/Storage and put it in the zip
                    file_name = f"{photo.category.replace(' ', '_')}_{os.path.basename(photo.image.name)}"
                    zip_file.writestr(file_name, photo.image.read())
                except Exception as e:
                    print(f"Error zipping photo {photo.id}: {e}")

    # Send the ZIP file to the browser
    response = HttpResponse(zip_buffer.getvalue(), content_type='application/zip')
    response['Content-Disposition'] = f'attachment; filename="{site.site_id}_Drone_Capture.zip"'
    return response
