from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.views import View
from django.http import JsonResponse, HttpResponse
from django.core.paginator import Paginator
from django.utils.decorators import method_decorator
from django.utils.dateformat import format
from django.utils import timezone

import pandas as pd
import os
import json

from .models import UploadSheet, MissingDataFile, WorkAssignment
from .utils import sanitize_username

# home
@login_required
def home(request):
    return render(request, 'home.html')

# upload sheet
@login_required
def upload_sheet(request):
    if request.method == 'GET':
        files = UploadSheet.objects.filter(user=request.user).order_by('-created_at')
        return render(request, 'upload_sheet.html', { 'files': files })
    
    elif request.method == 'POST':
        excel_file = request.FILES['file']
        if not excel_file.name.endswith('.xlsx'):
            return JsonResponse({'error': 'File is not an Excel file'}, status=400)

        # Save the file
        uploaded_file = UploadSheet.objects.create(user=request.user, file=excel_file)

        # Convert timestamps to the local timezone
        created_at_local = timezone.localtime(uploaded_file.created_at)
        updated_at_local = timezone.localtime(uploaded_file.updated_at)

        return JsonResponse({
            'success': 'File uploaded successfully.',
            'file': {
                'name': os.path.basename(uploaded_file.file.name),
                'uploaded_user': uploaded_file.uploaded_user,
                'created_at': format(created_at_local, 'N j, Y, P'),
                'updated_at': format(updated_at_local, 'N j, Y, P'),
            }
        })

# upload sheet actions to process file
@method_decorator(login_required, name='dispatch')
class UploadSheetActions(View):
    def get(self, request):
        file_name = request.GET.get('file_name')
        action = request.GET.get('action')

        username = sanitize_username(request.user.username)

        user_dir_path = os.path.join('uploads', f"user_{username}", 'uploaded_sheets')
        output_dir_path = os.path.join(user_dir_path, 'output')

        file_path = os.path.join(user_dir_path, file_name)
        file_base_name = os.path.splitext(file_name)[0]

        content_type='application/vnd.ms-excel'
        if action == 'download':
            file_to_download = f"{file_base_name}_output.csv"

        elif action == 'bookmark':
            file_to_download = f"{file_base_name}_missing.csv"
            
        elif action == 'red_download':
            file_to_download = f"{file_base_name}_summary.txt"
            content_type = 'text/plain'
            
        elif action == 'yellow_download':
            file_to_download = f"{file_base_name}_missing_companies.csv"
        
        else:
            return JsonResponse({ 'error': 'Invalid action button.' }, status=404)

        file_path = os.path.join(output_dir_path, file_to_download)
        if os.path.exists(file_path):
            with open(file_path, 'rb') as f:
                response = HttpResponse(f.read(), content_type=content_type)
                response['Content-Disposition'] = f'attachment; filename={file_to_download}'
                return response
        else:
            return JsonResponse({'error': 'File not found'}, status=404)

        

    def post(self, request):
        data = json.loads(request.body)
        action = data.get('action', None)
        file_name = data.get('file_name', None)

        if not action:
            return JsonResponse({ 'error': 'Action name is required!'}, status=400)
        
        if not action:
            return JsonResponse({ 'error': 'Action name is required!'}, status=400)
        
        
        # ================= File Processing ==============
        # create directory for the user
        username = sanitize_username(request.user.username)

        user_dir_path = os.path.join('uploads', f"user_{username}", 'uploaded_sheets')
        output_dir_path = os.path.join(user_dir_path, 'output')

        # Create the directory if it does not exist
        if not os.path.exists(output_dir_path):
            os.makedirs(output_dir_path)

        file_path = os.path.join(user_dir_path, file_name)
        file_base_name, file_extension = os.path.splitext(file_name)[0], os.path.splitext(file_name)[1].lower()

        try:
            if file_extension == '.csv':
                df = pd.read_csv(file_path)
            elif file_extension == '.xlsx':
                df = pd.read_excel(file_path, engine='openpyxl')
        except:
            return JsonResponse({ 'error': 'File either deleted or does not exist. Re-upload!'}, status=400)

        # -------------------- processing into output
        df['email']= "NA"

        # save to files
        df.to_csv(f"{output_dir_path}/{file_base_name}_output.csv")
        df.to_csv(f"{output_dir_path}/{file_base_name}_missing.csv")
        df.to_csv(f"{output_dir_path}/{file_base_name}_missing_companies.csv")

        # Open the file in write mode
        with open(f"{output_dir_path}/{file_base_name}_summary.txt", 'w') as file:
            # Write content to the file
            file.write("Emails are generated.") 

        # -----------------------------------------
        if action not in ['download', 'bookmark', 'red_download', 'yellow_download']:
            return JsonResponse({ 'error': 'Invalid action button.' }, status=400)

        # file download will be call to GET request from frontend
        return JsonResponse({'message': 'File processed successfully'}, status=200)

# missing data
@login_required
def missing_data(request):
    return render(request, 'missing_data.html')
    
    
@login_required
def get_paginated_data(request):
    try:
        page = int(request.GET.get('page', 1))
        per_page = int(request.GET.get('per_page', 100))
        search_term = request.GET.get('search_term', '')
    except ValueError:
        return JsonResponse({'error': 'Invalid page or per_page parameter'}, status=400)

    work_assignment = WorkAssignment.objects.filter(assigned_user=request.user, active=True).first()

    if work_assignment and work_assignment.assigned_file:
        file_path = work_assignment.assigned_file.path
        file_extension = os.path.splitext(file_path)[1].lower()

        try:
            if file_extension == '.csv':
                df = pd.read_csv(file_path)
            elif file_extension == '.xlsx':
                df = pd.read_excel(file_path, engine='openpyxl')
            else:
                return JsonResponse({'error': 'Unsupported file format'}, status=400)
        except Exception as e:
            return JsonResponse({'error': f'Error reading file: {e}'}, status=500)

        # Convert NaN values to empty strings
        df = df.fillna('')

        original_indices = df.index.tolist()  # Keep track of original indices

        # Filter by search term if provided
        if search_term:
            df = df[df['Company'].str.contains(search_term, case=False, na=False)]
            original_indices = df.index.tolist()

        start_row = 0
        end_row = len(df)
        total_rows = end_row - start_row

        # Paginate within the assigned rows
        paginated_start_row = start_row + (page - 1) * per_page
        paginated_end_row = min(paginated_start_row + per_page, end_row)
        paginated_data = df.iloc[paginated_start_row:paginated_end_row]

        response_data = {
            'columns': paginated_data.columns.tolist(),
            'data': paginated_data.values.tolist(),
            'total_pages': (total_rows // per_page) + (1 if total_rows % per_page > 0 else 0),
            'current_page': page,
            'start_row': paginated_start_row + 1,  # Convert back to 1-based index for display
            'total_rows': end_row + 1,
            'original_indices': original_indices[paginated_start_row:paginated_end_row]
        }
        return JsonResponse(response_data)

    return JsonResponse({'error': 'No data file assigned'}, status=400)


@login_required
def save_edited_data(request):
    try:
        data = json.loads(request.body)
        row_data = data.get('data', [])
        row_index = int(data.get('index', -1))
    except (ValueError, TypeError):
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)

    work_assignment = WorkAssignment.objects.filter(assigned_user=request.user, active=True).first()
    if not work_assignment or not work_assignment.assigned_file:
        return JsonResponse({'error': 'No data file assigned or invalid row index'}, status=400)

    file_path = work_assignment.assigned_file.path
    file_extension = os.path.splitext(file_path)[1].lower()

    try:
        if file_extension == '.csv':
            df = pd.read_csv(file_path)
        elif file_extension == '.xlsx':
            df = pd.read_excel(file_path, engine='openpyxl')
        else:
            return JsonResponse({'error': 'Unsupported file format'}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'Error reading file: {e}'}, status=500)

    # Convert the row_data to match the data types of the DataFrame columns
    for col_index, col in enumerate(df.columns):
        if col == 'Sr No':
            row_data[col_index] = pd.to_numeric(row_data[col_index])
        else:
            row_data[col_index] = str(row_data[col_index])

    # Validate the row index within the assigned range
    start_row = 0  # Convert to 0-based index
    end_row = len(df)

    if row_index != -1 and (row_index < start_row or row_index >= end_row):
        return JsonResponse({'error': 'Row index out of assigned range'}, status=400)

    if row_index == -1:
        # Add a new row to the DataFrame
        df.loc[len(df)] = row_data
    else:
        # Update the specific row in the DataFrame
        df.iloc[row_index] = row_data

    try:
        # Save the updated DataFrame back to the file
        if file_extension == '.csv':
            df.to_csv(file_path, index=False)
        elif file_extension == '.xlsx':
            df.to_excel(file_path, index=False, engine='openpyxl')
    except Exception as e:
        return JsonResponse({'error': f'Error saving file: {e}'}, status=500)

    # Update the updated_at field in WorkAssignment
    work_assignment.updated_at = timezone.now()
    work_assignment.save()

    return JsonResponse({'message': 'Row updated successfully'})


@login_required
def skip_row(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            sr_no = int(data.get('sr_no', -1))
            row_data = data.get('data', [])
        except (ValueError, TypeError):
            return JsonResponse({'error': 'Invalid JSON data'}, status=400)

        print("data: ", data, sr_no)
        work_assignment = WorkAssignment.objects.filter(assigned_user=request.user, active=True).first()
        if not work_assignment or not work_assignment.assigned_file:
            return JsonResponse({'error': 'No data file assigned or invalid row index'}, status=400)

        file_path = work_assignment.assigned_file.path
        file_extension = os.path.splitext(file_path)[1].lower()

        try:
            if file_extension == '.csv':
                df = pd.read_csv(file_path)
            elif file_extension == '.xlsx':
                df = pd.read_excel(file_path, engine='openpyxl')
            else:
                return JsonResponse({'error': 'Unsupported file format'}, status=400)
        except Exception as e:
            return JsonResponse({'error': f'Error reading file: {e}'}, status=500)

        # Find the row index based on Sr No
        row_index = df[df['Sr No'] == sr_no].index
        if row_index.empty:
            return JsonResponse({'error': 'Sr No not found in the data'}, status=400)

        row_index = row_index[0]  # Get the first match

        # Create or update the skipped rows file
        skipped_rows_file_dir = f'uploads/user_{request.user.username}/skipped_rows_files'
        skipped_rows_file_path = os.path.join(skipped_rows_file_dir, 'skipped_rows.csv')

        # Ensure the directory exists
        os.makedirs(skipped_rows_file_dir, exist_ok=True)

        if work_assignment.skipped_rows_file and os.path.exists(work_assignment.skipped_rows_file.path):
            skipped_df = pd.read_csv(work_assignment.skipped_rows_file.path)
        else:
            skipped_df = pd.DataFrame(columns=df.columns)

        skipped_row = pd.DataFrame([row_data], columns=skipped_df.columns)
        skipped_df = pd.concat([skipped_df, skipped_row], ignore_index=True)

        try:
            skipped_df.to_csv(skipped_rows_file_path, index=False)
            if not work_assignment.skipped_rows_file:
                work_assignment.skipped_rows_file = skipped_rows_file_path
                work_assignment.save()
        except Exception as e:
            return JsonResponse({'error': f'Error saving skipped rows file: {e}'}, status=500)

        # Remove the specific row in the DataFrame using the row index
        df.drop(df.index[row_index], inplace=True)

        try:
            # Save the updated DataFrame back to the original file
            if file_extension == '.csv':
                df.to_csv(file_path, index=False)
            elif file_extension == '.xlsx':
                df.to_excel(file_path, index=False, engine='openpyxl')
        except Exception as e:
            return JsonResponse({'error': f'Error saving file: {e}'}, status=500)

        # Update the updated_at field in WorkAssignment
        work_assignment.updated_at = timezone.now()
        work_assignment.save()

        return JsonResponse({'message': 'Row skipped successfully'})