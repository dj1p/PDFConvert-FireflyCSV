from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from pathlib import Path
import shutil
import uuid
from converter import BankStatementConverter
import uvicorn

app = FastAPI(title="Bank Statement PDF to CSV Converter")

UPLOAD_DIR = Path("/app/uploads")
OUTPUT_DIR = Path("/app/outputs")

UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

@app.get("/")
async def root():
    return {
        "message": "Bank Statement PDF to CSV Converter API",
        "endpoints": {
            "/convert": "POST - Upload PDF file to convert to CSV",
            "/health": "GET - Health check"
        }
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.post("/convert")
async def convert_pdf(file: UploadFile = File(...)):
    """
    Upload a PDF bank statement and receive a CSV file compatible with Firefly III
    """
    
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")
    
    # Generate unique ID for this conversion
    job_id = str(uuid.uuid4())
    
    # Save uploaded file
    input_path = UPLOAD_DIR / f"{job_id}_{file.filename}"
    output_path = OUTPUT_DIR / f"{job_id}_firefly.csv"
    
    try:
        # Save uploaded file
        with input_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Convert PDF to CSV
        converter = BankStatementConverter(input_path, output_path)
        converter.convert()
        
        # Return the CSV file
        return FileResponse(
            path=output_path,
            media_type="text/csv",
            filename=f"{Path(file.filename).stem}_firefly.csv"
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Conversion failed: {str(e)}")
    
    finally:
        # Cleanup uploaded file
        if input_path.exists():
            input_path.unlink()

@app.post("/convert-json")
async def convert_pdf_json(file: UploadFile = File(...)):
    """
    Upload a PDF bank statement and receive JSON data (useful for N8n)
    """
    
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")
    
    # Generate unique ID for this conversion
    job_id = str(uuid.uuid4())
    
    # Save uploaded file
    input_path = UPLOAD_DIR / f"{job_id}_{file.filename}"
    output_path = OUTPUT_DIR / f"{job_id}_firefly.csv"
    
    try:
        # Save uploaded file
        with input_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Convert PDF to CSV
        converter = BankStatementConverter(input_path, output_path)
        converter.convert()
        
        # Read CSV and return as JSON
        import pandas as pd
        df = pd.read_csv(output_path)
        
        return JSONResponse(content={
            "success": True,
            "filename": file.filename,
            "rows": len(df),
            "data": df.to_dict(orient='records'),
            "csv_content": df.to_csv(index=False)
        })
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Conversion failed: {str(e)}")
    
    finally:
        # Cleanup
        if input_path.exists():
            input_path.unlink()
        if output_path.exists():
            output_path.unlink()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
