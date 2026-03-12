from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy

from . import views

urlpatterns = [
    # Main labeling view (shows next unvalidated document)
    path("", views.labeling_view, name="labeling"),
    # Specific document view (for admin/re-labeling)
    path(
        "document/<int:doc_id>/", views.labeling_document_view, name="labeling_document"
    ),
    # Lock management endpoints
    path("api/release-lock/", views.release_lock_view, name="release_lock"),
    path(
        "api/check-lock/<int:doc_id>/",
        views.check_lock_status,
        name="check_lock_status",
    ),
    # Auth routes
    path(
        "login/", auth_views.LoginView.as_view(template_name="login.html"), name="login"
    ),
    path(
        "logout/",
        auth_views.LogoutView.as_view(
            next_page=reverse_lazy(
                "login"
            )  # you can use your named URL here just like you use the **url** tag in your django template
        ),
        name="logout",
    ),
]
