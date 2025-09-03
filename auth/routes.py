from flask import Blueprint, request, render_template
from auth.services import handle_signup, handle_login

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        #return handle_signup(request.form)
        return handle_signup(request.get_json()) 
    return render_template('register.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # return handle_login(request.form)
        return handle_login(request.get_json())
    return render_template('login.html')

from flask import redirect, session

@auth_bp.route('/logout')
def logout():
    session.pop('user', None)
    return redirect('/')
