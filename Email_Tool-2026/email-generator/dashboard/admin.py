from typing import Any
from django.contrib import admin
from django.contrib.auth.models import Group
from django.contrib import messages


from .models import UploadSheet, MissingDataFile, WorkAssignment
from .forms import MissingDataFileAdminForm

class UploadSheetAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'uploaded_user', 'get_filename', 'created_at', 'updated_at', )

    def get_filename(self, obj):
        return obj.filename()
    get_filename.short_description = 'File'


class MissingDataFileAdmin(admin.ModelAdmin):
    form = MissingDataFileAdminForm
    list_display = ('id', 'get_filename', 'no_of_rows', 'created_at', 'updated_at')

    def get_filename(self, obj):
        return obj.filename()
    get_filename.short_description = 'File'

    def save_model(self, request, obj, form, change):
        # Set the number of rows from the cleaned data
        df = form.cleaned_data['dataframe']
        obj.no_of_rows = len(df)
        
        # Save the instance
        super().save_model(request, obj, form, change)

    def delete_queryset(self, request, queryset):
        # Loop through each MissingDataFile instance in the queryset
        for obj in queryset:
            if obj.work_assignments.exists():
                # Add a message for the admin interface
                messages.error(request, f"Cannot delete '{obj}' because it is associated with a WorkAssignment.")
                return
        # If all objects are safe to delete, call the superclass method
        super().delete_queryset(request, queryset)


class WorkAssignmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'get_filename', 'assigned_user', 'active', 'start_row', 'end_row', 'get_no_of_rows', 'created_at', 'updated_at')
    list_select_related = ('missing_data_file',)
    ordering = ('missing_data_file__file',)
    exclude = ('assigned_file', 'skipped_rows_file', )

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return self.readonly_fields + ('assigned_file', 'skipped_rows_file', 'start_row', 'end_row', 'missing_data_file', 'assigned_user')
        return self.readonly_fields

    def get_filename(self, obj):
        return obj.filename()
    get_filename.short_description = 'File'
    get_filename.admin_order_field = 'missing_data_file__file'

    def get_no_of_rows(self, obj):
        try:
            return obj.missing_data_file.no_of_rows
        except:
            return 0
    get_no_of_rows.short_description = 'File Rows'

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "missing_data_file" and request._obj_ is not None:
            kwargs["queryset"] = db_field.related_model.objects.filter(pk=request._obj_.missing_data_file.pk)
        if db_field.name == "assigned_user" and request._obj_ is not None:
            kwargs["queryset"] = db_field.related_model.objects.filter(pk=request._obj_.assigned_user.pk)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def get_form(self, request, obj=None, **kwargs):
        request._obj_ = obj
        form = super().get_form(request, obj, **kwargs)
        return form


admin.site.register(UploadSheet, UploadSheetAdmin)
admin.site.register(MissingDataFile, MissingDataFileAdmin)
admin.site.register(WorkAssignment, WorkAssignmentAdmin)
admin.site.unregister(Group)