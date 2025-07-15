"""PDF Reader Tool for extracting resume content from PDF files."""

import os
from pathlib import Path
from typing import Dict, Any

import fitz  # PyMuPDF
from pydantic import BaseModel, Field
from google.adk.tools import FunctionTool
from google.adk.tools import ToolContext



class PDFReaderOutput(BaseModel):
    success: bool = Field(description="Whether the PDF was successfully read")
    content: str = Field(description="Extracted text content from the PDF", default="")
    hyperlinks: list = Field(description="Extracted hyperlinks from the PDF", default_factory=list)
    error_message: str = Field(description="Error message if reading failed", default="")
    metadata: Dict[str, Any] = Field(description="PDF metadata", default_factory=dict)


def read_pdf(tool_context: ToolContext) -> PDFReaderOutput:
    """
    Extract text content from a PDF file in the resume/ directory.
    
    Args:
        file_path: Resume filename (will look in resume/ directory) or leave empty to auto-detect
        
    Returns:
        PDFReaderOutput with extracted content and metadata
    """
    try:
        # Define the resume directory path
        resume_dir = Path(__file__).parent.parent.parent / "resume"
        
        pdf_files = list(resume_dir.glob("*.pdf"))
        if not pdf_files:
            return PDFReaderOutput(
                success=False,
                error_message="No PDF files found in resume/ directory"
            )
        full_path = pdf_files[0]
        
        if not full_path.exists():
            return PDFReaderOutput(
                success=False,
                error_message=f"File not found: {full_path}"
            )
        
        if not str(full_path).lower().endswith('.pdf'):
            return PDFReaderOutput(
                success=False,
                error_message="File must be a PDF"
            )
        
        # Open and read PDF
        doc = fitz.open(str(full_path))
        content = ""
        hyperlinks = []
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            
            # Extract text content
            content += page.get_text()
            content += "\n\n"  # Add spacing between pages
            
            # Extract hyperlinks from this page
            links = page.get_links()
            for link in links:
                if link.get('kind') == fitz.LINK_URI:  # External URI link
                    uri = link.get('uri', '')
                    if uri:
                        # Get the text content within the link area
                        rect = fitz.Rect(link['from'])
                        link_text = page.get_textbox(rect).strip()
                        
                        hyperlinks.append({
                            'url': uri,
                            'text': link_text if link_text else uri,
                            'page': page_num + 1,
                            'type': 'uri'
                        })
                elif link.get('kind') == fitz.LINK_GOTO:  # Internal link
                    # For internal links, we might still want to capture them
                    rect = fitz.Rect(link['from'])
                    link_text = page.get_textbox(rect).strip()
                    
                    hyperlinks.append({
                        'url': f"internal_page_{link.get('page', 'unknown')}",
                        'text': link_text,
                        'page': page_num + 1,
                        'type': 'internal'
                    })
        
        # Also try to extract URLs from text using regex (for non-clickable URLs)
        import re
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+|www\.[^\s<>"{}|\\^`\[\]]+|[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        text_urls = re.findall(url_pattern, content, re.IGNORECASE)
        
        for url in text_urls:
            # Only add if not already in hyperlinks
            if not any(link['url'] == url for link in hyperlinks):
                hyperlinks.append({
                    'url': url,
                    'text': url,
                    'page': 'text_extraction',
                    'type': 'text_found'
                })
        
        # Get metadata
        metadata = {
            "page_count": len(doc),
            "file_size": os.path.getsize(str(full_path)),
            "file_name": full_path.name,
            "hyperlinks_found": len(hyperlinks)
        }
        
        doc.close()
        
        tool_context.state["resume_analysis"] = content
        tool_context.state["resume_hyperlinks"] = hyperlinks

        return PDFReaderOutput(
            success=True,
            content=content.strip(),
            hyperlinks=hyperlinks,
            metadata=metadata
        )
        
    except Exception as e:
        return PDFReaderOutput(
            success=False,
            error_message=f"Error reading PDF: {str(e)}"
        )


# Create the FunctionTool
pdf_reader_tool = FunctionTool(read_pdf)