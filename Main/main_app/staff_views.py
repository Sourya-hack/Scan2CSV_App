import json

from django.contrib import messages
from django.core.files.storage import FileSystemStorage
from django.http import HttpResponse, JsonResponse
from django.shortcuts import (HttpResponseRedirect, get_object_or_404,redirect, render)
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
import pandas as pd
import PyPDF2
from .forms import *
from .models import *


def staff_home(request):
    staff = get_object_or_404(Staff, admin=request.user)
    total_students = Student.objects.filter(course=staff.course).count()
    total_leave = LeaveReportStaff.objects.filter(staff=staff).count()
    subjects = Subject.objects.filter(staff=staff)
    total_subject = subjects.count()
    attendance_list = Attendance.objects.filter(subject__in=subjects)
    total_attendance = attendance_list.count()
    attendance_list = []
    subject_list = []
    for subject in subjects:
        attendance_count = Attendance.objects.filter(subject=subject).count()
        subject_list.append(subject.name)
        attendance_list.append(attendance_count)
    context = {
        'page_title': 'Staff Panel - ' + str(staff.admin.last_name) + ' (' + str(staff.course) + ')',
        'total_students': total_students,
        'total_attendance': total_attendance,
        'total_leave': total_leave,
        'total_subject': total_subject,
        'subject_list': subject_list,
        'attendance_list': attendance_list
    }
    return render(request, 'staff_template/home_content.html', context)


def staff_take_attendance(request):
    staff = get_object_or_404(Staff, admin=request.user)
    subjects = Subject.objects.filter(staff_id=staff)
    sessions = Session.objects.all()
    context = {
        'subjects': subjects,
        'sessions': sessions,
        'page_title': 'Take Attendance'
    }

    return render(request, 'staff_template/staff_take_attendance.html', context)


@csrf_exempt
def get_students(request):
    subject_id = request.POST.get('subject')
    session_id = request.POST.get('session')
    try:
        subject = get_object_or_404(Subject, id=subject_id)
        session = get_object_or_404(Session, id=session_id)
        students = Student.objects.filter(
            course_id=subject.course.id, session=session)
        student_data = []
        for student in students:
            data = {
                    "id": student.id,
                    "name": student.admin.last_name + " " + student.admin.first_name
                    }
            student_data.append(data)
        return JsonResponse(json.dumps(student_data), content_type='application/json', safe=False)
    except Exception as e:
        return e



@csrf_exempt
def save_attendance(request):
    student_data = request.POST.get('student_ids')
    date = request.POST.get('date')
    subject_id = request.POST.get('subject')
    session_id = request.POST.get('session')
    students = json.loads(student_data)
    try:
        session = get_object_or_404(Session, id=session_id)
        subject = get_object_or_404(Subject, id=subject_id)

        # Check if an attendance object already exists for the given date and session
        attendance, created = Attendance.objects.get_or_create(session=session, subject=subject, date=date)

        for student_dict in students:
            student = get_object_or_404(Student, id=student_dict.get('id'))

            # Check if an attendance report already exists for the student and the attendance object
            attendance_report, report_created = AttendanceReport.objects.get_or_create(student=student, attendance=attendance)

            # Update the status only if the attendance report was newly created
            if report_created:
                attendance_report.status = student_dict.get('status')
                attendance_report.save()

    except Exception as e:
        return None

    return HttpResponse("OK")


def staff_update_attendance(request):
    staff = get_object_or_404(Staff, admin=request.user)
    subjects = Subject.objects.filter(staff_id=staff)
    sessions = Session.objects.all()
    context = {
        'subjects': subjects,
        'sessions': sessions,
        'page_title': 'Update Attendance'
    }

    return render(request, 'staff_template/staff_update_attendance.html', context)


@csrf_exempt
def get_student_attendance(request):
    attendance_date_id = request.POST.get('attendance_date_id')
    try:
        date = get_object_or_404(Attendance, id=attendance_date_id)
        attendance_data = AttendanceReport.objects.filter(attendance=date)
        student_data = []
        for attendance in attendance_data:
            data = {"id": attendance.student.admin.id,
                    "name": attendance.student.admin.last_name + " " + attendance.student.admin.first_name,
                    "status": attendance.status}
            student_data.append(data)
        return JsonResponse(json.dumps(student_data), content_type='application/json', safe=False)
    except Exception as e:
        return e


@csrf_exempt
def update_attendance(request):
    student_data = request.POST.get('student_ids')
    date = request.POST.get('date')
    students = json.loads(student_data)
    try:
        attendance = get_object_or_404(Attendance, id=date)

        for student_dict in students:
            student = get_object_or_404(
                Student, admin_id=student_dict.get('id'))
            attendance_report = get_object_or_404(AttendanceReport, student=student, attendance=attendance)
            attendance_report.status = student_dict.get('status')
            attendance_report.save()
    except Exception as e:
        return None

    return HttpResponse("OK")


def staff_apply_leave(request):
    form = LeaveReportStaffForm(request.POST or None)
    staff = get_object_or_404(Staff, admin_id=request.user.id)
    context = {
        'form': form,
        'leave_history': LeaveReportStaff.objects.filter(staff=staff),
        'page_title': 'Apply for Leave'
    }
    if request.method == 'POST':
        if form.is_valid():
            try:
                obj = form.save(commit=False)
                obj.staff = staff
                obj.save()
                messages.success(
                    request, "Application for leave has been submitted for review")
                return redirect(reverse('staff_apply_leave'))
            except Exception:
                messages.error(request, "Could not apply!")
        else:
            messages.error(request, "Form has errors!")
    return render(request, "staff_template/staff_apply_leave.html", context)


def staff_feedback(request):
    form = FeedbackStaffForm(request.POST or None)
    staff = get_object_or_404(Staff, admin_id=request.user.id)
    context = {
        'form': form,
        'feedbacks': FeedbackStaff.objects.filter(staff=staff),
        'page_title': 'Add Feedback'
    }
    if request.method == 'POST':
        if form.is_valid():
            try:
                obj = form.save(commit=False)
                obj.staff = staff
                obj.save()
                messages.success(request, "Feedback submitted for review")
                return redirect(reverse('staff_feedback'))
            except Exception:
                messages.error(request, "Could not Submit!")
        else:
            messages.error(request, "Form has errors!")
    return render(request, "staff_template/staff_feedback.html", context)


def staff_view_profile(request):
    staff = get_object_or_404(Staff, admin=request.user)
    form = StaffEditForm(request.POST or None, request.FILES or None,instance=staff)
    context = {'form': form, 'page_title': 'View/Update Profile'}
    if request.method == 'POST':
        try:
            if form.is_valid():
                first_name = form.cleaned_data.get('first_name')
                last_name = form.cleaned_data.get('last_name')
                password = form.cleaned_data.get('password') or None
                address = form.cleaned_data.get('address')
                gender = form.cleaned_data.get('gender')
                passport = request.FILES.get('profile_pic') or None
                admin = staff.admin
                if password != None:
                    admin.set_password(password)
                if passport != None:
                    fs = FileSystemStorage()
                    filename = fs.save(passport.name, passport)
                    passport_url = fs.url(filename)
                    admin.profile_pic = passport_url
                admin.first_name = first_name
                admin.last_name = last_name
                admin.address = address
                admin.gender = gender
                admin.save()
                staff.save()
                messages.success(request, "Profile Updated!")
                return redirect(reverse('staff_view_profile'))
            else:
                messages.error(request, "Invalid Data Provided")
                return render(request, "staff_template/staff_view_profile.html", context)
        except Exception as e:
            messages.error(
                request, "Error Occured While Updating Profile " + str(e))
            return render(request, "staff_template/staff_view_profile.html", context)

    return render(request, "staff_template/staff_view_profile.html", context)


@csrf_exempt
def staff_fcmtoken(request):
    token = request.POST.get('token')
    try:
        staff_user = get_object_or_404(CustomUser, id=request.user.id)
        staff_user.fcm_token = token
        staff_user.save()
        return HttpResponse("True")
    except Exception as e:
        return HttpResponse("False")


def staff_view_notification(request):
    staff = get_object_or_404(Staff, admin=request.user)
    notifications = NotificationStaff.objects.filter(staff=staff)
    context = {
        'notifications': notifications,
        'page_title': "View Notifications"
    }
    return render(request, "staff_template/staff_view_notification.html", context)


# def staff_add_result(request):
#     staff = get_object_or_404(Staff, admin=request.user)
#     subjects = Subject.objects.filter(staff=staff)
#     sessions = Session.objects.all()
#     context = {
#         'page_title': 'Result Upload',
#         'subjects': subjects,
#         'sessions': sessions
#     }

#     if request.method == 'POST':
#         # File upload branch
#         if request.FILES.get('result_file'):
#             file = request.FILES['result_file']
#             success = process_uploaded_file(file, staff)
#             if success:
#                 messages.success(request, "File processed and marks uploaded successfully.")
#             else:
#                 messages.error(request, "Error processing file. Please check the format.")
#             return render(request, "staff_template/staff_add_result.html", context)

#         # Manual entry branch (existing code)
#         try:
#             student_id = request.POST.get('student_list')
#             subject_id = request.POST.get('subject')
#             test = request.POST.get('test')
#             exam = request.POST.get('exam')
#             student = get_object_or_404(Student, id=student_id)
#             subject = get_object_or_404(Subject, id=subject_id)
#             try:
#                 data = StudentResult.objects.get(student=student, subject=subject)
#                 data.exam = exam
#                 data.test = test
#                 data.save()
#                 messages.success(request, "Scores Updated")
#             except:
#                 result = StudentResult(student=student, subject=subject, test=test, exam=exam)
#                 result.save()
#                 messages.success(request, "Scores Saved")
#         except Exception as e:
#             messages.warning(request, "Error Occured While Processing Form")
#     return render(request, "staff_template/staff_add_result.html", context)
def staff_add_result(request):
    staff = get_object_or_404(Staff, admin=request.user)
    subjects = Subject.objects.filter(staff=staff)
    sessions = Session.objects.all()
    context = {
        'page_title': 'Result Upload',
        'subjects': subjects,
        'sessions': sessions
    }

    if request.method == 'POST':
        # Handle bulk PDF upload
        if 'bulk_upload' in request.POST:
            session_id = request.POST.get('session')
            file = request.FILES.get('pdf_file')

            if not session_id or not file:
                messages.error(request, "Session and PDF file are required.")
                return render(request, "staff_template/staff_add_result.html", context)

            session = get_object_or_404(Session, id=session_id)
            course = staff.course
            results = parse_pdf_bulk_results(file, session, course)

            added = 0
            for item in results:
                try:
                    student = Student.objects.get(roll_number=item['roll'], session=session)
                    for sub_name, mark in item['marks'].items():
                        subject = Subject.objects.filter(name__icontains=sub_name.strip(), course=course).first()
                        if subject:
                            StudentResult.objects.update_or_create(
                                student=student,
                                subject=subject,
                                defaults={'exam': mark}
                            )
                            added += 1
                except Exception as e:
                    print(f"Error saving result: {e}")

            messages.success(request, f"Processed and saved {added} results from PDF.")
            return render(request, "staff_template/staff_add_result.html", context)

        # Handle manual entry
        else:
            try:
                student_id = request.POST.get('student_list')
                subject_id = request.POST.get('subject')
                test = request.POST.get('test')
                exam = request.POST.get('exam')
                student = get_object_or_404(Student, id=student_id)
                subject = get_object_or_404(Subject, id=subject_id)
                try:
                    result = StudentResult.objects.get(student=student, subject=subject)
                    result.test = test
                    result.exam = exam
                    result.save()
                    messages.success(request, "Scores Updated")
                except StudentResult.DoesNotExist:
                    StudentResult.objects.create(student=student, subject=subject, test=test, exam=exam)
                    messages.success(request, "Scores Saved")
            except Exception as e:
                messages.error(request, "Error Occurred While Processing Manual Entry")

    return render(request, "staff_template/staff_add_result.html", context)


@csrf_exempt
def fetch_student_result(request):
    try:
        subject_id = request.POST.get('subject')
        student_id = request.POST.get('student')
        student = get_object_or_404(Student, id=student_id)
        subject = get_object_or_404(Subject, id=subject_id)
        result = StudentResult.objects.get(student=student, subject=subject)
        result_data = {
            'exam': result.exam,
            'test': result.test
        }
        return HttpResponse(json.dumps(result_data))
    except Exception as e:
        return HttpResponse('False')



def extract_data_from_pdf(file):
    """Enhanced PDF parsing with regex patterns"""
    pdf_reader = PyPDF2.PdfReader(file)
    text = ''
    
    for page in pdf_reader.pages:
        text += page.extract_text() + '\n'
    
    # Define regex patterns
    patterns = {
        'name': r'(?i)(?:student name|name)[:\s]*([^\n]+)',
        'roll': r'(?i)(?:roll number|roll no|roll)[:\s]*([^\n]+)',
        'marks': r'(?i)(\b\w+\b)\s*:\s*(\d+\.?\d*)'
    }
    
    extracted_data = {
        'name': None,
        'roll': None,
        'marks': {}
    }
    
    # Extract name and roll number
    extracted_data['name'] = re.search(patterns['name'], text)
    extracted_data['roll'] = re.search(patterns['roll'], text)
    
    # Extract subject marks
    marks = re.findall(patterns['marks'], text)
    for subject, mark in marks:
        if subject.lower() not in ['total', 'percentage']:
            extracted_data['marks'][subject.strip()] = float(mark)
    
    # Clean extracted values
    if extracted_data['name']:
        extracted_data['name'] = extracted_data['name'].group(1).strip()
    if extracted_data['roll']:
        extracted_data['roll'] = extracted_data['roll'].group(1).strip()
    
    return extracted_data

def process_uploaded_file(file, staff):
    try:
        if file.name.endswith('.pdf'):
            data = extract_data_from_pdf(file)
            
            if not data['name'] or not data['roll']:
                raise ValueError("Missing required fields in PDF")
            
            student = Student.objects.get(roll_number=data['roll'])
            
            for subject_name, mark in data['marks'].items():
                subject = Subject.objects.get(
                    name__icontains=subject_name.strip(),
                    staff=staff
                )
                StudentResult.objects.update_or_create(
                    student=student,
                    subject=subject,
                    defaults={'exam': mark}
                )
            
            return True
            
    except Exception as e:
        print(f"Error processing PDF: {str(e)}")
        return False



# Add to imports
import csv
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
import re

def export_results_csv(request):
    # Authorization check
    
    # Get filter parameters
    student_id = request.GET.get('student_id')
    subject_id = request.GET.get('subject_id')
    
    # Build queryset
    results = StudentResult.objects.all()
    if student_id:
        results = results.filter(student__id=student_id)
    if subject_id:
        results = results.filter(subject__id=subject_id)
    
    # Create CSV response
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="student_results.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Roll Number', 'Student Name', 'Subject', 'Test Marks', 'Exam Marks', 'Total'])
    
    for result in results:
        total = result.test + result.exam
        writer.writerow([
            result.student.roll_number,
            f"{result.student.admin.last_name}, {result.student.admin.first_name}",
            result.subject.name,
            result.test,
            result.exam,
            total
        ])
    
    return response

def export_results_pdf(request):
    # Authorization check
    
    # Get filter parameters
    student_id = request.GET.get('student_id')
    subject_id = request.GET.get('subject_id')
    
    # Build queryset
    results = StudentResult.objects.select_related('student', 'subject')
    if student_id:
        results = results.filter(student__id=student_id)
    if subject_id:
        results = results.filter(subject__id=subject_id)
    
    # Create PDF document
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="student_results.pdf"'
    
    doc = SimpleDocTemplate(response, pagesize=letter)
    elements = []
    styles = getSampleStyleSheet()
    
    # Add title
    elements.append(Paragraph("Student Results Report", styles['Title']))
    
    # Create table data
    data = [['Roll No.', 'Student Name', 'Subject', 'Test', 'Exam', 'Total']]
    for result in results:
        total = result.test + result.exam
        data.append([
            result.student.roll_number,
            f"{result.student.admin.last_name}, {result.student.admin.first_name}",
            result.subject.name,
            str(result.test),
            str(result.exam),
            str(total)
        ])
    
    # Create table
    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.grey),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 12),
        ('BOTTOMPADDING', (0,0), (-1,0), 12),
        ('BACKGROUND', (0,1), (-1,-1), colors.beige),
        ('GRID', (0,0), (-1,-1), 1, colors.black)
    ]))
    
    elements.append(table)
    doc.build(elements)
    
    return response



def parse_pdf_bulk_results(file, session, course):
    import fitz
    import re
    results = []

    try:
        doc = fitz.open(stream=file.read(), filetype="pdf")
        for page in doc:
            text = page.get_text()
            roll_match = re.search(r'Roll\s*No(?:\.|:)?\s*([^\n]+)', text, re.IGNORECASE) or \
                         re.search(r'Roll\s*Number(?:\.|:)?\s*([^\n]+)', text, re.IGNORECASE)
            name_match = re.search(r'Name(?:\.|:)?\s*([^\n]+)', text, re.IGNORECASE)

            roll = roll_match.group(1).strip() if roll_match else None
            name = name_match.group(1).strip() if name_match else None

            # CASE A: tabular format (like "DATA STRUCTURE AND ALGORITHM T A 8 3.0 24.0")
            table_subjects = re.findall(r'([A-Z\s/()\-]+)[\s]+[TPMS]\s+[A-EO]\s+(\d+)', text)
            marks_dict = {}

            for subj, grade_point in table_subjects:
                subj = subj.strip()
                if subj.lower() not in ['total', 'sgpa', 'cgpa']:
                    marks_dict[subj] = float(grade_point)

            # CASE B: Web Development-style
            if not marks_dict:
                sub_match = re.search(r'Subject\s*[:\-]?\s*([^\n]+)', text, re.IGNORECASE)
                mark_match = re.search(r'Marks\s*[:\-]?\s*(\d+)', text, re.IGNORECASE)
                if sub_match and mark_match:
                    marks_dict[sub_match.group(1).strip()] = float(mark_match.group(1))

            if roll and name and marks_dict:
                results.append({
                    'roll': roll,
                    'name': name,
                    'marks': marks_dict
                })

    except Exception as e:
        print(f"PDF parse error: {e}")
    return results
