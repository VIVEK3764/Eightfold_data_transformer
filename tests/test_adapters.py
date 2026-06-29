import os
import sys
import pytest
from unittest.mock import MagicMock, patch, mock_open

# Add project root to sys.path so we can run this script directly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.adapters.csv_adapter import parse_csv
from src.adapters.ats_adapter import parse_ats
from src.adapters.resume_adapter import parse_resume
from src.adapters.notes_adapter import parse_notes

# --- CSV Adapter Tests ---

def test_csv_adapter_extraction():
    """
    Verify CSV loads correctly, email and phone normalization is applied.
    """
    csv_content = """name,email,phone,current_company,title
John Doe, JOHN@GMAIL.COM , 9876543210 ,Google,SDE"""
    
    # Mock opening the file
    with patch("builtins.open", mock_open(read_data=csv_content)):
        with patch("os.path.exists", return_value=True):
            profiles = parse_csv("mock_recruiter.csv")
            
    assert len(profiles) == 1
    prof = profiles[0]
    assert prof["source"] == "csv"
    assert prof["full_name"] == "John Doe"
    assert prof["emails"] == ["john@gmail.com"]      # Normalized
    assert prof["phones"] == ["+919876543210"]        # Normalized
    assert prof["current_company"] == "Google"
    assert prof["headline"] == "SDE"

# --- ATS Adapter Tests ---

def test_ats_adapter_mappings():
    """
    Verify ATS field mappings work, and missing fields are handled.
    """
    ats_json = """{
        "candidateName": "Jane Smith",
        "contactEmail": "jane@gmail.com",
        "currentEmployer": "Microsoft",
        "jobTitle": "Principal Architect"
    }"""
    
    with patch("builtins.open", mock_open(read_data=ats_json)):
        with patch("os.path.exists", return_value=True):
            profiles = parse_ats("mock_ats.json")
            
    assert len(profiles) == 1
    prof = profiles[0]
    assert prof["source"] == "ats"
    assert prof["full_name"] == "Jane Smith"
    assert prof["emails"] == ["jane@gmail.com"]
    assert prof["current_company"] == "Microsoft"
    assert prof["headline"] == "Principal Architect"
    assert prof["phones"] == []  # Missing phone handled gracefully

# --- Resume DOCX Tests ---

@patch("src.adapters.resume_adapter.docx")
def test_resume_docx_extraction(mock_docx):
    """
    Verify Word document parsing, email, phone, and skills extraction.
    """
    # Setup mock document structure
    mock_doc = MagicMock()
    mock_para1 = MagicMock(text="Jane Doe\nEmail: jane.doe@yahoo.com\nPhone: 9876543210\n")
    mock_para2 = MagicMock(text="Skills:\nJava\nPython\nspringboot\n")
    mock_doc.paragraphs = [mock_para1, mock_para2]
    mock_docx.Document.return_value = mock_doc
    
    with patch("os.path.exists", return_value=True):
        profiles = parse_resume("mock_resume.docx")
        
    assert len(profiles) == 1
    prof = profiles[0]
    assert prof["source"] == "resume"
    assert prof["full_name"] == "Jane Doe"
    assert "jane.doe@yahoo.com" in prof["emails"]
    assert "+919876543210" in prof["phones"]
    assert "Java" in prof["skills"]
    assert "Python" in prof["skills"]
    assert "Spring Boot" in prof["skills"]  # Normalized

# --- Resume PDF Tests ---

@patch("src.adapters.resume_adapter.pdfplumber")
def test_resume_pdf_extraction(mock_pdfplumber):
    """
    Verify PDF direct extraction works.
    """
    mock_pdf = MagicMock()
    mock_page = MagicMock()
    mock_page.extract_text.return_value = "John Architect Doe\njohn@doe.com\nPhone: (+91)-98765-43210\nSkills:\ncpp\njavascript\n"
    mock_pdf.pages = [mock_page]
    mock_pdfplumber.open.return_value.__enter__.return_value = mock_pdf
    
    with patch("os.path.exists", return_value=True):
        profiles = parse_resume("mock_resume.pdf")
        
    assert len(profiles) == 1
    prof = profiles[0]
    assert prof["source"] == "resume"
    assert prof["full_name"] == "John Architect Doe"
    assert "john@doe.com" in prof["emails"]
    assert "+919876543210" in prof["phones"]
    assert "C++" in prof["skills"]          # Normalized
    assert "JavaScript" in prof["skills"]   # Normalized

# --- OCR Fallback Test ---

@patch("src.adapters.resume_adapter.pdfplumber")
@patch("src.adapters.resume_adapter.pdf2image")
@patch("src.adapters.resume_adapter.pytesseract")
def test_resume_pdf_ocr_fallback(mock_tesseract, mock_pdf2image, mock_pdfplumber):
    """
    Mock empty direct text extraction and verify OCR fallback path executes.
    """
    # 1. Mock pdfplumber to return empty string (simulating image-only PDF)
    mock_pdf = MagicMock()
    mock_page = MagicMock()
    mock_page.extract_text.return_value = ""
    mock_pdf.pages = [mock_page]
    mock_pdfplumber.open.return_value.__enter__.return_value = mock_pdf
    
    # 2. Mock pdf2image and pytesseract values
    mock_pdf2image.convert_from_path.return_value = [MagicMock()]
    mock_tesseract.image_to_string.return_value = "OCR Candidate\nocr@gmail.com\n"
    
    with patch("os.path.exists", return_value=True):
        profiles = parse_resume("mock_scanned.pdf")
        
    # Verify OCR fallback was executed
    mock_pdf2image.convert_from_path.assert_called_once_with("mock_scanned.pdf")
    mock_tesseract.image_to_string.assert_called_once()
    
    assert len(profiles) == 1
    prof = profiles[0]
    assert prof["full_name"] == "OCR Candidate"
    assert prof["emails"] == ["ocr@gmail.com"]

# --- Notes Adapter Tests ---

def test_notes_adapter_extraction():
    """
    Verify Notes adapter extracts skills and company mentions correctly.
    """
    notes_text = """Candidate has strong Java and AWS experience.
Worked at Google for 5 years."""
    
    with patch("builtins.open", mock_open(read_data=notes_text)):
        with patch("os.path.exists", return_value=True):
            profiles = parse_notes("mock_notes.txt")
            
    assert len(profiles) == 1
    prof = profiles[0]
    assert prof["source"] == "notes"
    assert "Java" in prof["skills"]
    assert "AWS" in prof["skills"]
    assert prof["current_company"] == "Google"

if __name__ == "__main__":
    sys.exit(pytest.main([__file__]))
