import sys
sys.path.append('../../')
from auto_applier import evaluate_job_fit

job = {
    'title': 'Senior Software Engineer',
    'company': 'Google',
    'description': 'We are looking for a C++ developer with 10 years of experience.'
}
print('Fit:', evaluate_job_fit(job))
