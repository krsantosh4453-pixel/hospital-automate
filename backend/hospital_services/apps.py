from django.apps import AppConfig


class HospitalServicesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "hospital_services"
    verbose_name = "Hospital services (OT, ambulance, mortuary, CSSD, laundry, HR, feedback, templates)"
