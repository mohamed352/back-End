from django.http import JsonResponse
from django.db import IntegrityError
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.contrib.auth import authenticate, login, logout
import json
import datetime
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import get_object_or_404
from django.core.handlers.wsgi import WSGIRequest

from .models import Patient, Doctor, Appointment, User, PatientReconData, Message, Notification, TimeSlot


def handle_patient_file(file, appointment):
    if not file:
        return

    allowed_types = ['image/jpeg', 'image/png', 'application/pdf']
    if file.content_type not in allowed_types:
        raise ValueError("Unsupported file type.")

    appointment.patient_file = file
    appointment.save()


@csrf_exempt
@require_http_methods(["POST"])
def RegisterUser(request):
    data = request.POST
    profile_picture = request.FILES.get('profile_picture')
    username = data.get("username")
    email = data.get("email")
    password = data.get("password")
    confirmation = data.get("confirmation")
    first_name = data.get("first_name")
    last_name = data.get("last_name")
    user_type = data.get("type")
    specialization = data.get("specialization")
    clinic_location = data.get("clinic_location")
    time_slot_id = data.get("time_slot_id")

    if password != confirmation:
        return JsonResponse({"message": "Password and confirmation do not match."}, status=406)

    try:
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
        )
        user.profile_picture = profile_picture
        user.type = user_type
        print("Done USer save")

        if user_type == "Doctor":
            # time_slot = TimeSlot.objects.get(pk=time_slot_id)
            print("Done doctor")
            print(TimeSlot.objects.get(pk=time_slot_id))
            time_slot = get_object_or_404(TimeSlot, id=time_slot_id)
            print("Done")

            Doctor.objects.create(user=user, specialization=specialization,
                                  clinic_location=clinic_location, available_slots=time_slot)
            print("Done")
        elif user_type == "patient":
            Patient.objects.create(user=user)
        user.save()
        return JsonResponse({"message": "User registered successfully."}, status=201)
    except IntegrityError:
        return JsonResponse({"message": "Username already taken."}, status=400)
    except Exception as e:
        return JsonResponse({"message": str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def LoginUser(request):
    """Logs in a user"""
    if request.method != "POST":
        return JsonResponse({"error": "POST request is required."}, status=400)

    data = json.loads(request.body)
    username = data.get("username")
    password = data.get("password")
    print(username, password)
    user = authenticate(request, username=username, password=password)

    if user is not None:
        if data.get("type") == "patient":
            patient = Patient.objects.get(user=user)
            if patient is None:
                return JsonResponse({"message": "Username, type and/or password is incorrect"}, status=406)
        elif data.get("type") == "Doctor":
            doctor = Doctor.objects.get(user=user)
            if doctor is None:
                return JsonResponse({"message": "Username, type and/or password is incorrect"}, status=406)

        login(request, user)
        return JsonResponse({"message": "User successfully logged in."}, status=202)
    else:
        return JsonResponse({"message": "Username, type and/or password is incorrect"}, status=406)


@csrf_exempt
@login_required
@require_http_methods(["POST"])
def LogoutUser(request):
    """Logs out the current user"""
    logout(request)
    return JsonResponse({"message": "Logged out"}, status=202)


@login_required
@require_http_methods(["GET"])
def CurrentUser(request):
    """Gets details about the current user"""
    user_type = request.user.type
    if user_type == "patient":
        return JsonResponse(Patient.objects.get(user=request.user).full_serialize(), status=200)
    elif user_type == "Doctor":
        return JsonResponse(Doctor.objects.get(user=request.user).full_serialize(), status=200)
    else:
        return JsonResponse({"message": f"{request.user.username} is not a patient or a doctor"}, status=401)


@csrf_exempt
@login_required
@require_http_methods(["POST"])
def RequestAppointment(request):
    if request.content_type == 'multipart/form-data':
        date = request.POST.get('date')
        time_slot_id = request.POST.get('time_slot_id')
        patient_message = request.POST.get('patient_message')
        doctor_id = request.POST.get('doctor_id')
        patient_file = request.FILES.get('patient_file', None)
    else:
        try:
            data = json.loads(request.body)
            date = data.get('date')
            time_slot_id = data.get('time_slot_id')
            patient_message = data.get('patient_message')
            doctor_id = data.get('doctor_id')
            patient_file = None
        except json.JSONDecodeError:
            return JsonResponse({"error": "Malformed JSON or empty body"}, status=400)

    try:
        doctor = Doctor.objects.get(pk=doctor_id)
        time_slot = TimeSlot.objects.get(pk=time_slot_id)
        patient = Patient.objects.get(user=request.user)

        appointment = Appointment(
            date=date,
            request_time_slot=time_slot,
            patient_message=patient_message,
            patient=patient,
            doctor=doctor,
            patient_file=patient_file
        )
        appointment.save()
        return JsonResponse({"message": "Appointment successfully requested."}, status=201)
    except Doctor.DoesNotExist:
        return JsonResponse({"error": "Doctor not found"}, status=404)
    except TimeSlot.DoesNotExist:
        return JsonResponse({"error": "Time slot not found"}, status=404)
    except Patient.DoesNotExist:
        return JsonResponse({"error": "Patient not found"}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@login_required
@require_http_methods(["PUT"])
def EditAppointment(request):
    """Edits an appointment if the user is a patient"""
    if request.user.type != "patient":
        return JsonResponse({"error": "This operation is only valid for patients"}, status=400)

    data = json.loads(request.body)
    date = data.get("date")
    request_time_slot_id = data.get("request_time_slot_id")
    patient_message = data.get("patient_message")
    appointment_id = data.get("appointment_id")
    patient_file = request.FILES.get('patient_file', None)

    try:
        date = datetime.datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        return JsonResponse({"error": "Invalid date format. Use YYYY-MM-DD."}, status=400)

    date_today = datetime.datetime.today().date()
    if date < date_today + datetime.timedelta(days=1):
        return JsonResponse({"message": "Appointments must have dates later than today."}, status=406)
    elif date > date_today + datetime.timedelta(days=8):
        return JsonResponse({"message": "Appointments can only be booked for this week."}, status=406)

    time_slot = TimeSlot.objects.filter(pk=request_time_slot_id).first()
    if not time_slot:
        return JsonResponse({"message": "Invalid time slot."}, status=406)

    try:
        appointment = Appointment.objects.get(pk=appointment_id, patient=Patient.objects.get(user=request.user))
    except Appointment.DoesNotExist:
        return JsonResponse({"message": "Invalid Appointment ID."}, status=404)

    appointment.date = date
    appointment.request_time_slot = time_slot
    appointment.patient_message = patient_message
    if patient_file:
        appointment.patient_file = patient_file
    appointment.save()

    return JsonResponse({"message": "Appointment successfully edited."}, status=200)


@csrf_exempt
@login_required
@require_http_methods(["DELETE"])
def DeleteAppointment(request, appointment_id):
    """Deletes an appointment if the user is a patient"""
    if request.user.type != "patient":
        return JsonResponse(
            {"error": "This operation is only valid for patients"}, status=400)

    try:
        appointment = Appointment.objects.get(
            pk=appointment_id, patient=Patient.objects.get(user=request.user))
        appointment.delete()
        return JsonResponse({"message": "Appointment successfully deleted."}, status=202)
    except Appointment.DoesNotExist:
        return JsonResponse({"error": "Invalid Appointment ID."}, status=404)
    except Patient.DoesNotExist:
        return JsonResponse({"error": "Patient not found."}, status=404)


@login_required
@require_http_methods(["PUT"])
def AcceptAppointment(request):
    """Accepts an appointment if the user is a doctor"""
    if request.method != "PUT":
        return JsonResponse({"error": "PUT request is required."}, status=400)
    elif request.user.type != "Doctor":
        return JsonResponse(
            {"error", f"{request.user.username} is not a doctor, this is a valid operation only for doctors."},
            status=406)

    data = json.loads(request.body)
    doctor_message = data.get("doctor_message")
    appointment_id = data.get("appointment_id")

    try:
        accepted_start_time = datetime.datetime.strptime(
            data.get("accepted_start_time"), "%H:%M").time()
    except ValueError:
        return JsonResponse({"error": "Accepted Start Time is not valid."}, status=406)
    except TypeError:
        return JsonResponse({"error": "Accepted Start Time is required."}, status=406)

    appointment_queryset = Appointment.objects.filter(
        pk=appointment_id, doctor=Doctor.objects.get(user=request.user))
    if appointment_queryset.count() < 1:
        return JsonResponse({"message": "Invalid Appointment."}, status=406)

    appointment = appointment_queryset.first()

    request_time_slot = appointment.request_time_slot
    if request_time_slot != "Any":
        request_time_extremes = request_time_slot.split(" - ")
        time_slot_start = datetime.datetime.strptime(
            request_time_extremes[0], "%H:%M").time()
        time_slot_end = datetime.datetime.strptime(
            request_time_extremes[1], "%H:%M").time()
    else:
        time_slot_start = datetime.datetime.strptime(
            "9:00", "%H:%M").time()
        time_slot_end = datetime.datetime.strptime(
            "17:00", "%H:%M").time()

    if accepted_start_time < time_slot_start or accepted_start_time >= time_slot_end:
        return JsonResponse({
            "message": f"accepted_start_time should be on or after {time_slot_start} and be before {time_slot_end} for this appointment."},
            status=406)

    appointment.accepted = True
    appointment.accepted_start_time = accepted_start_time
    appointment.doctor_message = doctor_message
    appointment.save()

    #     here the notification implementation
    Notification.objects.create(
        user=appointment.patient.user,
        message=f"Your appointment with Dr. {appointment.doctor.user.username} on {appointment.date} has been accepted."
    )

    return JsonResponse({"message": "Appointment successfully accepted."}, status=202)


@login_required
@require_http_methods(["PUT"])
def RejectAppointment(request):
    """Rejects an appointments if the user is a doctor"""
    if request.method != "PUT":
        return JsonResponse({"error": "PUT request is required."}, status=400)
    elif request.user.type != "Doctor":
        return JsonResponse(
            {"error", f"{request.user.username} is not a doctor, this is a valid operation only for doctors."},
            status=406)

    data = json.loads(request.body)
    doctor_message = data.get("doctor_message")
    appointment_id = data.get("appointment_id")

    appointment_queryset = Appointment.objects.filter(
        pk=appointment_id, doctor=Doctor.objects.get(user=request.user))
    if appointment_queryset.count() < 1:
        return JsonResponse({"message": "Invalid Appointment."}, status=406)

    appointment = appointment_queryset.first()

    appointment.rejected = True
    appointment.doctor_message = doctor_message
    appointment.save()
    return JsonResponse({"message": "Appointment successfully rejected."}, status=202)


@login_required
@require_http_methods(["GET"])
def PatientAppointments(request):
    """Returns a list of appointments of a patient"""
    if request.user.type == "patient":
        appointments = Appointment.objects.filter(
            patient=Patient.objects.get(user=request.user))
        appointments = appointments.order_by("date").all()
        return JsonResponse({"appointments": [appointment.serialize_for_patient() for appointment in appointments]}, status=200)
    else:
        return JsonResponse({"message": f"{request.user.username} is not a patient or a doctor"}, status=401)


@login_required
@require_http_methods(["GET"])
def AcceptedDoctorAppointments(request):
    """Returns a list of accepted appointments of a doctor"""
    if request.user.type == "Doctor":
        appointments = Appointment.objects.filter(
            doctor=Doctor.objects.get(user=request.user), accepted=True)
        appointments = appointments.order_by("date").all()
        return JsonResponse({"appointments": [appointment.serialize_for_doctor() for appointment in appointments]},
                            status=200)
    else:
        return JsonResponse(
            {"message": f"{request.user.username} is not a doctor, this is a valid operation only for doctors"},
            status=401)


@login_required
@require_http_methods(["GET"])
def RequestedDoctorAppointments(request):
    """Returns a list of requested appointments of a doctor"""
    if request.user.type == "Doctor":
        appointments = Appointment.objects.filter(
            doctor=Doctor.objects.get(user=request.user), accepted=False, rejected=False)
        appointments = appointments.all()
        return JsonResponse({"appointments": [appointment.serialize_for_doctor() for appointment in appointments]},
                            status=200)
    else:
        return JsonResponse(
            {"message": f"{request.user.username} is not a doctor, this is a valid operation only for doctors"},
            status=401)


@require_http_methods(["GET"])
def AvailableDoctors(request):
    """Returns a list of doctors a patient currently doesn't have a pending or accepted appointment with"""
    if request.user.type == "patient":
        all_doctors = set(Doctor.objects.all())
        doctors_with_appointment_with_user = set([appointment.doctor for appointment in Patient.objects.get(
            user=request.user).appointments.filter(rejected=False)])
        doctors = all_doctors - doctors_with_appointment_with_user
        return JsonResponse({"doctors": [doctor.public_serialize() for doctor in doctors]}, status=200)
    else:
        return JsonResponse(
            {"message": f"{request.user.username} is not a patient, this is a valid operation only for patients"},
            status=400)


@csrf_exempt
@login_required
def PatientReconDataView(request):
    if request.user.type != "patient":
        return JsonResponse({"error": "This operation is only valid for patients"}, status=400)

    try:
        recon_file = request.FILES.get('recon_file')
        message = request.POST.get('message')

        if not recon_file or not message:
            return JsonResponse({"error": "Both file and message are required"}, status=400)

        # File type or size validation
        allowed_types = ['image/jpeg', 'image/png', 'application/pdf']
        if recon_file.content_type not in allowed_types:
            return JsonResponse({"error": "Unsupported file type"}, status=400)

        patient = Patient.objects.get(user=request.user)
        recon_data = PatientReconData(
            patient=patient,
            recon_file=recon_file,
            message=message
        )
        recon_data.save()

        return JsonResponse({"message": "Recon data successfully saved."}, status=201)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
@login_required
@require_http_methods(["POST"])
def SendMessage(request):
    data = json.loads(request.body)
    print(data)  # Debug print, can be removed in production
    sender = request.user
    receiver_username = data.get('receiver_username')
    content = data.get('content')
    print(sender, receiver_username, content)

    try:
        receiver = User.objects.get(username__iexact=receiver_username)
        message = Message.objects.create(sender=sender, receiver=receiver, content=content)
        print(receiver_username, content, "done")

        notification_message = f"You have received a new message from {sender.username}: {content}"
        Notification.objects.create(user=receiver, message=notification_message)

        return JsonResponse({"message": "Message sent successfully."}, status=201)
    except User.DoesNotExist:
        return JsonResponse({"error": "Receiver not found."}, status=404)


@login_required
def view_notifications(request):
    """
    Returns all notifications for the logged-in user.
    """
    notifications = Notification.objects.filter(user=request.user).order_by('-timestamp')
    notifications_data = [{
        'id': notification.id,
        'message': notification.message,
        'is_read': notification.is_read,
        'timestamp': notification.timestamp
    } for notification in notifications]

    # Optionally, you could mark notifications as read when they are fetched
    notifications.update(is_read=True)

    return JsonResponse({'notifications': notifications_data})
