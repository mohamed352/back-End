from django.urls import path

from .views import RegisterUser, LoginUser, LogoutUser, CurrentUser, AvailableDoctors, RequestAppointment, \
    PatientAppointments, RequestedDoctorAppointments, AcceptedDoctorAppointments, AcceptAppointment, RejectAppointment, \
    EditAppointment, DeleteAppointment, PatientReconDataView , SendMessage ,view_notifications

urlpatterns = [
    path('register', RegisterUser, name="register"),
    path('login', LoginUser, name="login"),
    path('logout', LogoutUser, name="logout"),
    path('current_user', CurrentUser, name="current_user"),
    path('available_doctors', AvailableDoctors, name="available_doctors"),
    path('request_appointment', RequestAppointment, name="request_appointment"),
    path('accept_appointment', AcceptAppointment, name="accept_appointment"),
    path('reject_appointment', RejectAppointment, name="reject_appointment"),
    path('patient_appointments', PatientAppointments,
         name="patient_appointments"),
    path('requested_doctor_appointments', RequestedDoctorAppointments,
         name="pending_doctor_appointments"),
    path('accepted_doctor_appointments', AcceptedDoctorAppointments,
         name="accepted_doctor_appointments"),
    path('edit_appointment', EditAppointment, name="edit_appointment"),
    path('delete_appointment', DeleteAppointment, name="delete_appointment"),
    path('delete_appointment/<int:appointment_id>', DeleteAppointment, name='delete-appointment'),
    path('patient-recon-data', PatientReconDataView, name='patient-recon-data'),
    path('send-message', SendMessage, name='send-message'),
    path('notifications', view_notifications, name='view_notifications'),

]
