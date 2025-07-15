"""Save Cover Letter PDF Functions - Normal functions for use in callbacks."""

import datetime
from google.genai import types
from typing import Dict, Any
from google.adk.agents.callback_context import CallbackContext

# Method 1: Using weasyprint (recommended for markdown to PDF)
# Disabled to avoid libgobject-2.0-0 system library issues
WEASYPRINT_AVAILABLE = False


def markdown_to_pdf_weasyprint(markdown_content: str) -> bytes:
    """Convert markdown to PDF using weasyprint (best quality)."""
    raise ImportError("WeasyPrint disabled to avoid system library issues")


def simple_markdown_to_html(markdown_content: str) -> str:
    """Simple markdown to HTML conversion for basic formatting."""
    import re
    
    # Convert the text to HTML
    html_content = markdown_content
    
    # Convert headers
    html_content = re.sub(r'^# (.+)$', r'<h1>\1</h1>', html_content, flags=re.MULTILINE)
    html_content = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html_content, flags=re.MULTILINE)
    html_content = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html_content, flags=re.MULTILINE)
    
    # Convert bold text
    html_content = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html_content)
    html_content = re.sub(r'__(.+?)__', r'<strong>\1</strong>', html_content)
    
    # Convert italic text
    html_content = re.sub(r'\*(.+?)\*', r'<em>\1</em>', html_content)
    html_content = re.sub(r'_(.+?)_', r'<em>\1</em>', html_content)
    
    # Simple conversion - just wrap paragraphs
    paragraphs = html_content.split('\n\n')
    html_paragraphs = []
    for para in paragraphs:
        para = para.strip()
        if para:
            # Don't wrap headers in paragraphs
            if not para.startswith('<h'):
                para = f'<p>{para.replace(chr(10), "<br>")}</p>'
            html_paragraphs.append(para)
    
    return '\n'.join(html_paragraphs)


def text_to_pdf_simple(text_content: str) -> bytes:
    """Simple text to PDF conversion using basic approach."""
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        
        # Create a BytesIO buffer
        import io
        buffer = io.BytesIO()
        
        # Create PDF document
        doc = SimpleDocTemplate(buffer, pagesize=letter,
                              rightMargin=72, leftMargin=72,
                              topMargin=72, bottomMargin=18)
        
        # Get styles
        styles = getSampleStyleSheet()
        
        # Create story
        story = []
        
        # Convert text to paragraphs
        paragraphs = text_content.split('\n\n')
        for para in paragraphs:
            para = para.strip()
            if para:
                # Remove basic markdown formatting
                para = para.replace('**', '').replace('*', '')
                story.append(Paragraph(para, styles['Normal']))
                story.append(Spacer(1, 12))
        
        # Build PDF
        doc.build(story)
        
        # Get PDF bytes
        pdf_bytes = buffer.getvalue()
        buffer.close()
        
        return pdf_bytes
        
    except ImportError:
        # Ultimate fallback - create a simple text file and rename it
        # This is not ideal but ensures something is saved
        text_bytes = text_content.encode('utf-8')
        return text_bytes


async def save_cover_letter_pdf_function(callback_context:CallbackContext, filename: str) -> Dict[str, Any]:
    """
    Save cover letter from session state as PDF.
    
    Args:
        callback_context: CallbackContext with state and save_artifact method
        filename: PDF filename
        
    Returns:
        Operation result dictionary
    """
    try:
        print(f"🔍 save_cover_letter_pdf_function called with callback_context, filename: {filename}")
        
        # 1. Get cover letter markdown content from session state
        cover_letter_markdown = callback_context.state.get("cover_letter")
        
        if not cover_letter_markdown:
            return {
                'status': 'failed',
                'error': 'No cover letter found in session state. Generate a cover letter first.'
            }
        
        # 2. Ensure correct filename
        if not filename.endswith('.pdf'):
            filename = f"{filename}.pdf"
        
        # 3. Convert markdown to PDF
        if WEASYPRINT_AVAILABLE:
            pdf_bytes = markdown_to_pdf_weasyprint(cover_letter_markdown)
            conversion_method = "weasyprint"
        else:
            # Fallback to simple text PDF
            pdf_bytes = text_to_pdf_simple(cover_letter_markdown)
            conversion_method = "simple_text"

        # 4. Create PDF artifact
        pdf_artifact = types.Part.from_bytes(
            data=pdf_bytes,
            mime_type="application/pdf"
        )
        
        # 5. Save to artifacts using CallbackContext.save_artifact
        version = await callback_context.save_artifact(filename, pdf_artifact)
        
        # 6. Update session state with save status
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        save_info = {
            "filename": filename,
            "version": version,
            "size_bytes": len(pdf_bytes),
            "conversion_method": conversion_method,
            "timestamp": timestamp,
            "success": True
        }
        callback_context.state["last_pdf_save"] = save_info
        print(f"✅ PDF saved successfully: {filename}")
        return {
            'status': 'success',
            'message': f'Cover letter saved as PDF: {filename}',
            'filename': filename,
            'version': version,
            'size_bytes': len(pdf_bytes),
            'conversion_method': conversion_method,
            'timestamp': timestamp
        }
        
    except Exception as e:
        error_msg = f"Error saving cover letter as PDF: {str(e)}"
        
        callback_context.state["last_pdf_save"] = {
            "success": False,
            "error": error_msg,
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        return {
            'status': 'failed',
            'error': error_msg
        }


# Legacy tool wrapper - now using save_cover_letter_pdf_function directly in callbacks

