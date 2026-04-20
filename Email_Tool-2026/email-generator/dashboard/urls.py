from django.contrib.auth import views as auth_views
from django.urls import path
from .views import home, upload_sheet, UploadSheetActions, missing_data, save_edited_data, skip_row, get_paginated_data

urlpatterns = [
    path('', home, name='home'),
    path('upload-sheet', upload_sheet, name='upload_sheet'),
    path('upload-sheet-actions', UploadSheetActions.as_view(), name='upload_sheet_actions'),
    path('missing-data', missing_data, name='missing_data'),
    path('get-paginated-data', get_paginated_data, name='get_paginated_data'),
    path('save-edited-data', save_edited_data, name='save_edited_data'),
    path('skip-row', skip_row, name='skip_row'),
    
    # auth views
    path('login', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('logout', auth_views.LogoutView.as_view(next_page="/login"), name='logout'),
]