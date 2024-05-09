from django.db import models
from django.contrib.auth.models import AbstractUser
from django.db.models.deletion import CASCADE
from datetime import timedelta, datetime

from django.db import models
from datetime import time


class TimeSlot(models.Model):
    start_time = models.TimeField()
    end_time = models.TimeField()

    @classmethod
    def initialize_slots(cls):
        # Define two time slots if they don't exist
        slots_data = [
            (time(9, 0), time(15, 0)),
            (time(15, 0), time(21, 0))
        ]
        for start, end in slots_data:
            cls.objects.get_or_create(start_time=start, end_time=end)

    def __str__(self):
        return f"{self.start_time.strftime('%H:%M')} - {self.end_time.strftime('%H:%M')}"


def profile_upload_path(instance, filename):
    return '/'.join(['profile_pictures', instance.username, filename])


class User(AbstractUser):
    profile_picture = models.ImageField(
        null=True, blank=True, upload_to=profile_upload_path)
    type = models.CharField(max_length=64, null=True, blank=True)

    def __str__(self) -> str:
        return f"{self.username} of type {self.type}"


class Patient(models.Model):
    user = models.ForeignKey(User, on_delete=CASCADE, related_name="patients")

    def __str__(self) -> str:
        return f"Patient {self.user.username}"

    def public_serialize(self):
        return {
            "id": self.pk,
            "first_name": self.user.first_name,
            "last_name": self.user.last_name,
            "profile_picture_url": self.user.profile_picture.url if self.user.profile_picture else None,
            "type": "patient",
        }

    def full_serialize(self):
        return {
            "id": self.pk,
            "username": self.user.username,
            "first_name": self.user.first_name,
            "last_name": self.user.last_name,
            "profile_picture_url": self.user.profile_picture.url if self.user.profile_picture else None,
            "type": "patient",
        }


class Doctor(models.Model):
    user = models.ForeignKey(User, on_delete=CASCADE, related_name="doctors")
    specialization = models.CharField(max_length=100)
    available_slots = models.ManyToManyField(TimeSlot, blank=True,null=True)  # Ensure this field is correctly defined
    clinic_location = models.CharField(max_length=255, default="Not Registered", null=True)  # New field

    def __str__(self) -> str:
        return f"Doctor {self.user.username}"

    def public_serialize(self):
        return {
            "id": self.pk,
            "first_name": self.user.first_name,
            "last_name": self.user.last_name,
            "specialization": self.specialization,
            "profile_picture_url": self.user.profile_picture.url if self.user.profile_picture else None,
            "type": "doctor",
            "clinic_location": self.clinic_location,  # Include in serialization
        }

    def full_serialize(self):
        return {
            "id": self.pk,
            "username": self.user.username,
            "first_name": self.user.first_name,
            "last_name": self.user.last_name,
            "specialization": self.specialization,
            "profile_picture_url": self.user.profile_picture.url if self.user.profile_picture else None,
            "type": "doctor",
            "clinic_location": self.clinic_location,  # Include in serialization
        }


class Appointment(models.Model):
    date = models.DateField()
    request_time_slot = models.ForeignKey(TimeSlot, on_delete=models.SET_NULL, null=True, blank=True)
    accepted_start_time = models.TimeField(null=True, blank=True)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="appointments")
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name="appointments")
    accepted = models.BooleanField(default=False)
    rejected = models.BooleanField(default=False)
    patient_message = models.CharField(max_length=280, null=True, blank=True)
    doctor_message = models.CharField(max_length=280, null=True, blank=True)
    patient_file = models.FileField(upload_to='patient_files/', null=True, blank=True)

    class Meta:
        unique_together = ('patient', 'doctor', 'date', 'request_time_slot')

    def __str__(self) -> str:
        slot = f"{self.request_time_slot.start_time.strftime('%H:%M')} - {self.request_time_slot.end_time.strftime('%H:%M')}" if self.request_time_slot else "Unscheduled"
        return f"{self.patient}'s appointment with {self.doctor} on {self.date} at {slot}"

    def serialize_for_patient(self):
        return {
            "id": self.pk,
            "doctor_details": self.doctor.public_serialize(),
            "accepted": self.accepted,
            "rejected": self.rejected,
            "date": self.date,
            "request_time_slot": self.request_time_slot.start_time.strftime(
                '%H:%M') + ' - ' + self.request_time_slot.end_time.strftime(
                '%H:%M') if self.request_time_slot else None,
            "accepted_start_time": self.accepted_start_time,
            "patient_message": self.patient_message,
            "doctor_message": self.doctor_message,
            "patient_file": self.patient_file.url if self.patient_file else None,
        }


class PatientReconData(models.Model):
    patient = models.ForeignKey('Patient', on_delete=models.CASCADE, related_name='recon_data')
    recon_file = models.FileField(upload_to='recon_files/', null=True, blank=True)
    message = models.TextField()
    medical_history_result = models.FileField(upload_to='medical_history/', editable=False, blank=True, null=True)

    def __str__(self):
        return f"Recon Data for {self.patient.user.username}"

    def serialize(self):
        return {
            "id": self.pk,
            "patient_id": self.patient.pk,
            "recon_file_url": self.recon_file.url if self.recon_file else None,
            "message": self.message,
            "result": self.result
        }


class Message(models.Model):
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sent_messages")
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name="received_messages")
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Message from {self.sender.username} to {self.receiver.username} at {self.timestamp}"


class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notifications")
    message = models.CharField(max_length=255)
    is_read = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Notification for {self.user.username}: {self.message}"
