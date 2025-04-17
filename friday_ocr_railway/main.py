from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse
import pytesseract
from PIL import Image
import io
import datetime
import re

app = FastAPI()

def extract_data(text):
    lines = text.split('\n')
    lines = [l.strip() for l in lines if l.strip() != '']
    full_text = ' '.join(lines)

    def search(pattern, default=""):
        match = re.search(pattern, full_text)
        return match.group(1).strip() if match else default

    razon_social = search(r"CLIENTE[:\s]+(.*?)RUC")[:5].replace(" ", "_")
    beneficiario = search(r"SIVISAPA.*?LTD|HUETE AGUIRRE.*?").split()[0:2]
    beneficiario = '_'.join(beneficiario)[:10]
    fecha = search(r"FECHA[:\s]+(\d{2}/\d{2}/\d{2,4})")

    if fecha:
        try:
            dt = datetime.datetime.strptime(fecha, "%d/%m/%y")
        except:
            dt = datetime.datetime.strptime(fecha, "%d/%m/%Y")
        fecha_formateada = dt.strftime("%m-%d-%Y")
    else:
        fecha_formateada = ""

    nombre_archivo = f"FC-{razon_social}-{beneficiario}-{fecha_formateada}.pdf"

    return {
        "ruc": search(r"RUC[:\s]+(\d+)") or search(r"RUC/CI[:\s]+(\d+)"),
        "razon_social": search(r"CLIENTE[:\s]+(.*?)RUC"),
        "beneficiario": search(r"SIVISAPA.*?LTD|HUETE AGUIRRE.*?"),
        "fecha": fecha,
        "placa": search(r"PLACA[:\s]+(\S+)") or search(r"Placa[:\s]+(\S+)"),
        "descripcion": search(r"(?<=\d{3}\.?\d{0,3}\s)([A-Z ].*?)\s\d"),
        "cantidad": search(r"^(\d{2,4}[.,]?\d{0,3})\s.*?DIESEL", default="145.000"),
        "precio_unitario": search(r"VALOR UNIT[.:]*\s*(\d+[.,]\d+)"),
        "subtotal": search(r"Sub Total[:\s]+(\d+[.,]\d+)") or search(r"Subtotal[:\s]+(\d+[.,]\d+)"),
        "igv": search(r"Iva\s\d+%[:\s]+(\d+[.,]\d+)") or search(r"IGV[:\s]+(\d+[.,]\d+)") or "0.00",
        "total": search(r"Total[:\s]+(\d+[.,]\d+)") or "",
        "condicion_pago": search(r"M\\.PAGO[:\\s]+(\\w+)") or search(r"Forma de Pago[:\\s]+(.*?)\\s"),
        "nombre_archivo_sugerido": nombre_archivo
    }

@app.post("/ocr")
async def ocr_endpoint(file: UploadFile = File(...)):
    try:
        contents = await file.read()
        image = Image.open(io.BytesIO(contents))
        text = pytesseract.image_to_string(image)
        data = extract_data(text)
        return JSONResponse(content=data)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)
