from django.shortcuts import render

def login_view(request):
	return render(request, 'users/login.html')


def register_view(request):
	branches = ['CSE', 'IT', 'ECE', 'EEE', 'Mechanical', 'Civil', 'Biotech']
	years = [1, 2, 3, 4, 5]
	return render(
		request,
		'users/register.html',
		{
			'branches': branches,
			'years': years,
		},
	)


def forgot_password_view(request):
	return render(request, 'users/forgot_password.html')


def email_verification_view(request):
	return render(request, 'users/email_verification.html')
