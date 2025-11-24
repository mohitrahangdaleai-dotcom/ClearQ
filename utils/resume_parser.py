import PyPDF2
from docx import Document
from config import Config

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS

def parse_resume(file):
    """Extract text from PDF or DOCX resume"""
    
    filename = file.filename.lower()
    
    if filename.endswith('.pdf'):
        return parse_pdf(file)
    elif filename.endswith('.docx'):
        return parse_docx(file)
    else:
        raise ValueError("Unsupported file format")

def parse_pdf(file):
    """Extract text from PDF file"""
    try:
        pdf_reader = PyPDF2.PdfReader(file)
        text = ""
        
        for page in pdf_reader.pages:
            text += page.extract_text()
        
        return text
    except Exception as e:
        raise Exception(f"Error reading PDF: {str(e)}")

def parse_docx(file):
    """Extract text from DOCX file"""
    try:
        doc = Document(file)
        text = ""
        
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"
        
        return text
    except Exception as e:
        raise Exception(f"Error reading DOCX: {str(e)}")