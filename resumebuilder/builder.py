# Import necessary libraries
from flask import Flask, render_template, request, jsonify, session, send_file
import groq
import json
from fpdf import FPDF

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Required for session management

# Initialize Groq Client
client = groq.Client(api_key="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")  # Replace with your actual API key

# Chatbot Questions
questions = [
    "Hi there! I'm ResumeBot. Let's build your resume! What is your name?",
    "Great! What is your email?",
    "Now, tell me about your education. What is your course?",
    "Which college did you study at for this course?",
    "What year did you complete it?",
    "Would you like to add another education detail? (yes/no)",
    "Now, let's talk about your skills. Enter a main skill:",
    "Here are 10 related sub-skills. Select the ones you have (comma-separated):",
    "Would you like to add another main skill? (yes/no)",
    "Do you have any certifications? (yes/no)",
    "Enter the certificate name:",
    "Enter the certificate ID:",
    "Where did you get this certification from?",
    "Would you like to add another certification? (yes/no)",
    "Tell me about your projects. What is the project name?",
    "Provide a brief description of the project:",
    "Enter the project repository link:",
    "Would you like to add another project? (yes/no)",
    "All done! Generating your resume now..."
]

@app.route('/')
def index():
    session.clear()  # Clear session on start
    session['step'] = 0
    session['data'] = {
        "name": "",
        "email": "",
        "education": [],
        "skills": [],
        "certifications": [],
        "projects": []
    }
    return render_template('chatbot.html')

@app.route('/chat', methods=['POST'])
def chat():
    user_input = request.json.get('message', '').strip().lower()
    step = session.get('step', 0)
    data = session.get('data', {})

    if not user_input:
        return jsonify({"question": "Please enter a valid response."})

    if step == 0:
        data['name'] = user_input
    elif step == 1:
        data['email'] = user_input
    elif step == 2:
        data['education'].append({"course": user_input})
    elif step == 3:
        data['education'][-1]['college'] = user_input
    elif step == 4:
        data['education'][-1]['year'] = user_input
    elif step == 5:  
        if user_input == 'no':
            session['step'] = 6
            return jsonify({"question": questions[6]})  
        else:
            session['step'] = 2  
            return jsonify({"question": questions[2]})

    elif step == 6:  
        data['skills'].append({"mainskill": user_input})

        # Fetch subskills from Groq API
        response = client.chat.completions.create(
            model="llama3-8b-8192",
            messages=[
                {"role": "system", "content": f"Generate a list of 10 related sub-skills for {user_input}. Return only a comma-separated list."},
                {"role": "user", "content": user_input}
            ]
        )
        
        subskills_raw = response.choices[0].message.content.strip()
        subskills = subskills_raw.split(", ")

        session['step'] = 7  
        return jsonify({"question": "Here are 10 related sub-skills. Select the ones you have (comma-separated):", "subskills": subskills})

    elif step == 7:  
        data['skills'][-1]['subskills'] = user_input.split(',')
        session['step'] = 8
        return jsonify({"question": "Would you like to add another main skill? (yes/no)"})

    elif step == 8:  
        if user_input == 'yes':
            session['step'] = 6  
            return jsonify({"question": "Enter another main skill:"})
        else:
            session['step'] = 9  
            return jsonify({"question": questions[9]})

    elif step == 9:  # Do you have any certifications?
        if user_input == 'yes':
            session['step'] = 10
            return jsonify({"question": questions[10]})  
        else:
            session['step'] = 14  # Skip to projects
            return jsonify({"question": questions[14]})

    elif step == 10:  # Enter the certificate name
        data['certifications'].append({"name": user_input})  # ✅ Fix: Add a new certificate entry
        session['step'] = 11
        return jsonify({"question": questions[11]})

    elif step == 11:  # Enter the certificate ID
        if not data['certifications']:  # Prevent IndexError
            return jsonify({"question": "Error: Please enter the certificate name first."})
        data['certifications'][-1]['id'] = user_input
        session['step'] = 12
        return jsonify({"question": questions[12]})

    elif step == 12:  # Enter certification source
        if not data['certifications']:  # Prevent IndexError
            return jsonify({"question": "Error: Please enter the certificate name first."})
        data['certifications'][-1]['source'] = user_input
        session['step'] = 13
        return jsonify({"question": questions[13]})

    elif step == 13:  # Add another certification?
        if user_input == 'no':
            session['step'] = 14
            return jsonify({"question": questions[14]})  
        else:
            session['step'] = 10  # Restart certification entry
            return jsonify({"question": questions[10]})
    elif step == 14:  # Ask for project name
        data['projects'].append({"name": user_input})  # ✅ Fix: Add a new project entry
        session['step'] = 15
        return jsonify({"question": questions[15]})

    elif step == 15:  # Ask for project description
        if not data['projects']:  # Prevent IndexError
            return jsonify({"question": "Error: Please enter the project name first."})
        data['projects'][-1]['description'] = user_input
        session['step'] = 16
        return jsonify({"question": questions[16]})

    elif step == 16:  # Ask for project technologies
        if not data['projects']:  # Prevent IndexError
            return jsonify({"question": "Error: Please enter the project name first."})
        data['projects'][-1]['technologies'] = user_input.split(", ")
        session['step'] = 17
        return jsonify({"question": questions[17]})

    elif step == 17:  # Ask if user wants to add another project
        if user_input == 'no':
            session['step'] = 18  # Move to the next section
            return jsonify({"question": questions[18]})  
        else:
            session['step'] = 14  # Restart project entry
            return jsonify({"question": questions[14]})

    session['step'] += 1
    session['data'] = data
    return jsonify({"question": questions[session['step']]})


@app.route('/generate')
def generate_resume():
    data = session.get('data', {})

    response = client.chat.completions.create(
        model="llama3-8b-8192",
        messages=[
            {"role": "system", "content": "You are a professional resume generator. Format the response as a polished with text decorations and paragraph seperations write in dtailed everydetail must have a minimum of 10 words, well-structured resume with clear sections, dont add new line in the same section, bullet points, and professional formatting. Ensure readability, proper alignment, and a concise presentation of information seperate each line after 7 words. 'DONT' include your intro part into the resume. i need only the info of the user into the resume"},
            {"role": "user", "content": json.dumps(data, indent=2)}
        ]
    )

    resume_text = (response.choices[0].message.content).replace("*","")

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.multi_cell(0, 10, resume_text)
    pdf_path = "E:/resumebuilder/resumebuilder/static/resume.pdf"
    pdf.output(pdf_path)
    
    return send_file(pdf_path, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
