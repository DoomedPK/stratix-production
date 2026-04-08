from .models import ActivityAlert, Site

def live_alerts(request):
    # If the user isn't logged in, don't try to fetch alerts
    if not request.user.is_authenticated:
        return {'recent_alerts': []}

    user = request.user
    
    # Grab the exact same role-based alerts we had in the dashboard view!
    if user.is_superuser or (hasattr(user, 'profile') and user.profile.role in ['Admin', 'QA']):
        recent_alerts = ActivityAlert.objects.all().order_by('-timestamp')[:6]
    elif hasattr(user, 'profile') and user.profile.role == 'Client':
        base_sites = Site.objects.filter(project__client=user.profile.client)
        recent_alerts = ActivityAlert.objects.filter(site__in=base_sites, alert_type='UPLOAD', message__icontains='Final').order_by('-timestamp')[:6]
    elif hasattr(user, 'profile') and user.profile.role == 'Tech Writer':
        recent_alerts = ActivityAlert.objects.filter(message__icontains='technical writing').order_by('-timestamp')[:6]
    else:
        base_sites = Site.objects.filter(assigned_contractors=user)
        recent_alerts = ActivityAlert.objects.filter(site__in=base_sites).order_by('-timestamp')[:6]

    # This makes 'recent_alerts' available to EVERY HTML file in your project automatically
    return {'recent_alerts': recent_alerts}
