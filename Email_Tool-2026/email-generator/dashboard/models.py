from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from io import BytesIO

import os
import re
import pandas as pd

# upload sheet screen
def uploaded_sheet_path(instance, filename):
    # MEDIA_ROOT / uploads/user_username/uploaded_sheets/<filename>
    return 'uploads/user_{0}/uploaded_sheets/{1}'.format(sanitize_username(instance.user.username), filename)

class UploadSheet(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    # track if user is deleted
    uploaded_user = models.CharField(max_length=150, null=True, blank=True)
    file = models.FileField(upload_to=uploaded_sheet_path)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if self.user:
            self.uploaded_user = self.user.username
        super().save(*args, **kwargs)

    def filename(self):
        return os.path.basename(self.file.name)

    def __str__(self):
        return self.file.name
    

# Upload sheet screen
def sanitize_username(username):
    return re.sub(r'[^\w\s-]', '', username).strip().lower()

def uploaded_missing_data_file_path(instance, filename):
    # MEDIA_ROOT / uploads/user_username/missing_data_files/<filename>
    return 'uploads/missing_data_files/{0}'.format(filename)

class MissingDataFile(models.Model):
    file = models.FileField(upload_to=uploaded_missing_data_file_path)
    no_of_rows = models.BigIntegerField(null=True, blank=True, editable=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    REQUIRED_COLUMNS = ['Company', 'Error', 'Add Domain', 'Mail Patterns']

    def filename(self):
        return os.path.basename(self.file.name)

    def __str__(self):
        return f'{os.path.basename(self.file.name)}'
    
    def delete(self, *args, **kwargs):
        # Debugging output
        print("self.work_assignments: ", self.work_assignments.all())
        
        # Check if there are any associated WorkAssignment instances
        if self.work_assignments.exists():
            raise ValidationError("Cannot delete MissingDataFile because it is associated with a WorkAssignment.")
        
        # Call the superclass method to perform the actual deletion
        super().delete(*args, **kwargs)



# Assign Work to Users
def assigned_missing_data_file_path(instance, filename):
    # MEDIA_ROOT / uploads/user_username/missing_data_files/<filename>
    return 'uploads/user_{0}/missing_data_files/{1}'.format(sanitize_username(instance.assigned_user.username), filename)

def skipped_rows_file_path(instance, filename):
    return 'uploads/user_{0}/skipped_rows_files/{1}'.format(sanitize_username(instance.assigned_user.username), filename)

class WorkAssignment(models.Model):
    missing_data_file = models.ForeignKey(MissingDataFile, on_delete=models.SET_NULL, null=True, blank=True, related_name='work_assignments')
    assigned_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_user')
    assigned_file = models.FileField(upload_to=assigned_missing_data_file_path, null=True, blank=True)
    skipped_rows_file = models.FileField(upload_to=skipped_rows_file_path, null=True, blank=True)
    active = models.BooleanField(default=True)

    start_row = models.BigIntegerField()
    end_row = models.BigIntegerField()

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    _skip_file_creation = False  # Internal flag to skip file creation during save

    def filename(self):
        try:
            return os.path.basename(self.missing_data_file.file.name)
        except:
            return None

    def __str__(self):
        return f'Work assigned to {self.assigned_user.username if self.assigned_user else "None"}'
    
    def clean(self):
        super().clean()

        if not self.start_row or not self.end_row:
            raise ValidationError("Both start row and end row are required")
        
        if self.start_row <= 0 or self.end_row <= 0:
            raise ValidationError("Start row index and end row index must be greater than 0.")
        
        if self.start_row > self.end_row:
            raise ValidationError("Start row index must be less than end row index.")

        if self.missing_data_file:
            if self.end_row > self.missing_data_file.no_of_rows:
                raise ValidationError(f"End row index must not exceed the total number of rows({self.missing_data_file.no_of_rows}) in the file. ")

            # Check for overlapping assignments
            if self.active:
                overlapping_assignments = WorkAssignment.objects.filter(
                    missing_data_file=self.missing_data_file,
                    active=True,
                    end_row__gte=self.start_row,
                    start_row__lte=self.end_row,
                ).exclude(id=self.id)

                if overlapping_assignments.exists():
                    raise ValidationError("Start and End row index of this assignment overlaps with another assignment for the same file.")
        
        if self.active and self.assigned_user:
            # Check for other active assignments for the same user
            other_active_assignments = WorkAssignment.objects.filter(
                assigned_user=self.assigned_user,
                active=True,
            ).exclude(id=self.id)

            if other_active_assignments.exists():
                raise ValidationError("The user already has an active work assignment. Please de-activate older one to activate this.")

    def save(self, *args, **kwargs):
        if self._skip_file_creation:
            print("Skipping file creation to avoid infinite loop.")
            super().save(*args, **kwargs)
            return
        
        self.clean()

        print("Entering save method.")
        generate_assigned_file = False

        if self.pk:
            print(f"Existing instance with PK: {self.pk}")
            old_instance = WorkAssignment.objects.get(pk=self.pk)
            if (old_instance.missing_data_file != self.missing_data_file or
                old_instance.start_row != self.start_row or
                old_instance.end_row != self.end_row):
                print("Relevant fields have changed, clearing assigned file.")
                self.assigned_file.delete(save=False)
                self.assigned_file = None
                generate_assigned_file = True
            else:
                print("No relevant changes detected.")
        else:
            print("New instance, setting flag to generate assigned file.")
            generate_assigned_file = True

        if generate_assigned_file and self.missing_data_file:
            print("Generating new assigned file.")
            self.missing_data_file.file.open()
            file_path = self.missing_data_file.file.path
            file_extension = os.path.splitext(file_path)[1].lower()

            try:
                if file_extension == '.csv':
                    df = pd.read_csv(file_path)
                elif file_extension == '.xlsx':
                    df = pd.read_excel(file_path, engine='openpyxl')
                else:
                    raise ValidationError("Unsupported file format")
                
                # Extract the required rows and columns
                required_columns = self.missing_data_file.REQUIRED_COLUMNS
                if any(col not in df.columns for col in required_columns):
                    raise ValidationError("One or more required columns are missing from the data file.")

                # create file with only required columns and 'Update date' & 'Sr No' column
                assigned_df = df.iloc[self.start_row-1:self.end_row][required_columns]
                
                # Remove duplicate rows based on the "Company" column
                assigned_df.drop_duplicates(subset="Company", inplace=True)
                
                # Add Sr No and Update date columns
                assigned_df.insert(0, 'Sr No', range(1, len(assigned_df)+1))
                assigned_df['Update date'] = ""

                if file_extension == '.csv':
                    file_content = assigned_df.to_csv(index=False).encode('utf-8')
                elif file_extension == '.xlsx':
                    buffer = BytesIO()
                    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                        assigned_df.to_excel(writer, index=False)
                    buffer.seek(0)
                    file_content = buffer.getvalue()

                new_file_name = f"{self.assigned_user.username}_{self.missing_data_file.filename()}_{self.start_row}_{self.end_row}{file_extension}"
                print(f"Saving new file: {new_file_name}")

                # Skip the next save call to avoid infinite loop
                self._skip_file_creation = True
                self.assigned_file.save(new_file_name, ContentFile(file_content))
                self._skip_file_creation = False

            except Exception as e:
                print(f"Error processing file: {e}")
                raise ValidationError(f"Error processing file: {e}")

        super().save(*args, **kwargs)
