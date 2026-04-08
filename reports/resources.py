from import_export import resources, fields
from import_export.widgets import ForeignKeyWidget
from .models import Site, Project, Client, UserProfile

class ProjectWidget(ForeignKeyWidget):
    def __init__(self, model, field, user=None, *args, **kwargs):
        self.user = user
        super().__init__(model, field, *args, **kwargs)

    def clean(self, value, row=None, **kwargs):
        if not value:
            return None
        
        project = self.model.objects.filter(name=value).first()
        
        if not project:
            profile = UserProfile.objects.filter(user=self.user).first()
            if profile and profile.client:
                project = self.model.objects.create(
                    name=value,
                    client=profile.client
                )
            else:
                raise ValueError(f"User '{self.user}' must be linked to a Client in User Profiles.")
                
        return project

class SiteResource(resources.ModelResource):
    project = fields.Field(
        column_name='project',
        attribute='project',
        widget=ProjectWidget(Project, 'name')
    )

    def __init__(self, user=None, **kwargs):
        super().__init__(**kwargs)
        self.user = user
        if 'project' in self.fields:
            self.fields['project'].widget.user = self.user

    class Meta:
        model = Site
        fields = ('site_id', 'site_name', 'project', 'location', 'latitude', 'longitude', 'priority')
        import_id_fields = ('site_id',)
        skip_unchanged = True
