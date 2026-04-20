from django import forms 
import pandas as pd
import os

from .models import MissingDataFile


class MissingDataFileAdminForm(forms.ModelForm):
    class Meta:
        model = MissingDataFile
        fields = ['file']

    def clean_file(self):
        file = self.cleaned_data.get('file')
        if not file:
            raise forms.ValidationError("File is required.")

        file_extension = os.path.splitext(file.name)[1].lower()

        try:
            if file_extension == '.csv':
                df = pd.read_csv(file)
            elif file_extension == '.xlsx':
                df = pd.read_excel(file, engine='openpyxl')
            else:
                raise forms.ValidationError("Unsupported file format")

            # Check for required columns
            print(df.columns)
            missing_columns = [col for col in MissingDataFile.REQUIRED_COLUMNS if col not in df.columns]
            if missing_columns:
                raise forms.ValidationError(f"The uploaded file is missing the following required columns: {', '.join(missing_columns)}")

            # Store the dataframe in the form for later use
            self.cleaned_data['dataframe'] = df

        except Exception as e:
            raise forms.ValidationError(f"Error processing file: {e}")

        return file