from django.shortcuts import render
from django.http import HttpResponseRedirect
# <HINT> Import any new Models here
from .models import Course, Enrollment, Question, Choice, Submission
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse
from django.views import generic
from django.contrib.auth import login, logout, authenticate
import logging
# Get an instance of a logger
logger = logging.getLogger(__name__)
# Create your views here.


def registration_request(request):
    context = {}
    if request.method == 'GET':
        return render(request, 'onlinecourse/user_registration_bootstrap.html', context)
    elif request.method == 'POST':
        # Check if user exists
        username = request.POST['username']
        password = request.POST['psw']
        first_name = request.POST['firstname']
        last_name = request.POST['lastname']
        user_exist = False
        try:
            User.objects.get(username=username)
            user_exist = True
        except:
            logger.error("New user")
        if not user_exist:
            user = User.objects.create_user(username=username, first_name=first_name, last_name=last_name,
                                            password=password)
            login(request, user)
            return redirect("onlinecourse:index")
        else:
            context['message'] = "User already exists."
            return render(request, 'onlinecourse/user_registration_bootstrap.html', context)


def login_request(request):
    context = {}
    if request.method == "POST":
        username = request.POST['username']
        password = request.POST['psw']
        user = authenticate(username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('onlinecourse:index')
        else:
            context['message'] = "Invalid username or password."
            return render(request, 'onlinecourse/user_login_bootstrap.html', context)
    else:
        return render(request, 'onlinecourse/user_login_bootstrap.html', context)


def logout_request(request):
    logout(request)
    return redirect('onlinecourse:index')


def check_if_enrolled(user, course):
    is_enrolled = False
    if user.id is not None:
        # Check if user enrolled
        num_results = Enrollment.objects.filter(user=user, course=course).count()
        if num_results > 0:
            is_enrolled = True
    return is_enrolled


# CourseListView
class CourseListView(generic.ListView):
    template_name = 'onlinecourse/course_list_bootstrap.html'
    context_object_name = 'course_list'

    def get_queryset(self):
        user = self.request.user
        courses = Course.objects.order_by('-total_enrollment')[:10]
        for course in courses:
            if user.is_authenticated:
                course.is_enrolled = check_if_enrolled(user, course)
        return courses


class CourseDetailView(generic.DetailView):
    model = Course
    template_name = 'onlinecourse/course_detail_bootstrap.html'


def enroll(request, course_id):
    course = get_object_or_404(Course, pk=course_id)
    user = request.user

    is_enrolled = check_if_enrolled(user, course)
    if not is_enrolled and user.is_authenticated:
        # Create an enrollment
        Enrollment.objects.create(user=user, course=course, mode='honor')
        course.total_enrollment += 1
        course.save()

    return HttpResponseRedirect(reverse(viewname='onlinecourse:course_details', args=(course.id,)))


# <HINT> Create a submit view to create an exam submission record for a course enrollment,
# you may implement it based on following logic:
         # Get user and course object, then get the associated enrollment object created when the user enrolled the course
         # Create a submission object referring to the enrollment
         # Collect the selected choices from exam form
         # Add each selected choice object to the submission object
         # Redirect to show_exam_result with the submission id
def submit(request, course_id):
    context = {}    
    if request.method == "POST":
        user = request.user
        if user.is_authenticated:
            course = get_object_or_404(Course, pk=course_id)
            is_enrolled = check_if_enrolled(user, course)
            if is_enrolled:
                enrollment = Enrollment.objects.get(user = user, course = course)
                choices = Choice.objects.filter(pk__in=extract_answers(request))
                submission = Submission.objects.create(enrollment = enrollment)
                submission.choices.set(choices)
                return redirect(reverse(viewname='onlinecourse:result', args=(course_id, submission.id)))
            else:
                return redirect('onlinecourse:index')
        else:
            return render(request, 'onlinecourse/user_login_bootstrap.html', context)
    else:
        return render(request, 'onlinecourse:index', context)

# <HINT> A example method to collect the selected choices from the exam form from the request object
def extract_answers(request):
    submitted_anwsers = []
    for key in request.POST:
        if key.startswith('choice'):
            value = request.POST[key]
            choice_id = int(value)
            submitted_anwsers.append(choice_id)
    return submitted_anwsers

class QuestionSubmission:
    def __init__(self, question, choice_array):
        self.question = question
        self.choice_array = choice_array

class ChoiceSubmission:
    def __init__(self, choice, submission_array):
        self.choice = choice
        self.submission_array = submission_array
    def answered_correctly(self):
        return self.submission_array.__contains__(self.choice.id)

# <HINT> Create an exam result view to check if learner passed exam and show their question results and result for each question,
# you may implement it based on the following logic:
        # Get course and submission based on their ids
        # Get the selected choice ids from the submission record
        # For each selected choice, check if it is a correct answer or not
        # Calculate the total score
#def show_exam_result(request, course_id, submission_id):
def show_exam_result(request, course_id, submission_id):
    context = {}    
    user = request.user
    if user.is_authenticated:
        course = get_object_or_404(Course, pk=course_id)        
        submission = get_object_or_404(Submission, pk=submission_id)
        questions = []
        submission_choice_ids = []
        total = 0
        total_possible_score = 0
        question_submissions = []
        for choice in submission.choices.all():
            if not questions.__contains__(choice.question):
                questions.append(choice.question)
            if not submission_choice_ids.__contains__(choice.id):
                submission_choice_ids.append(choice.id)
        for question in questions:
            total += question.is_get_score(submission_choice_ids)
            total_possible_score += question.grade
            choice_submissions = []
            for choice in question.choice_set.all():
                choice_submissions.append(ChoiceSubmission(choice, submission_choice_ids))
            question_submissions.append(QuestionSubmission(question, choice_submissions))
        percentage = total / total_possible_score * 100
        context['course'] = course
        context['submission'] = submission
        context['grade'] = percentage
        context['question_submissions'] = question_submissions
        return render(request, 'onlinecourse/exam_result_bootstrap.html', context)        
    else:
        return render(request, 'onlinecourse/user_login_bootstrap.html', context)    


