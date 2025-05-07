from fastapi import FastAPI, Query, HTTPException, Response
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from typing import List, Literal
from pydantic import BaseModel
import os
import ctypes
import numpy as np

# Importar mòdul chatbot
import sys
sys.path.append("chatbot")
from chatbot.chatbot import respond


app = FastAPI()

# Cargar la biblioteca compartida
lib = ctypes.CDLL('./build/libfunctions.so')


# Servir archivos estáticos (CSS, imágenes)
app.mount("/static", StaticFiles(directory="static"), name="static")


# ENDPOINTS
# ------------------------ INDEX -------------------------------------------------------------------------
@app.get("/")
async def serve_index():
    index_path = "static/index.html"
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"error": "index.html no encontrado"}



# ------------------------ EXPONENTS -------------------------------------------------------------------------
# Definir tipus d'arguments i retorn per exponents
lib.exponents.argtypes = (
    ctypes.c_float, 
    ctypes.c_char_p, 
    ctypes.c_float, 
    ctypes.c_float, 
    ctypes.c_float,
    ctypes.c_float,
    ctypes.c_float
)
lib.exponents.restype = ctypes.POINTER(ctypes.c_float)

# Funció que crida a la funció exponents
@app.get("/exponents")
async def exponents(
    M: float = Query(1, description="Modulation"), 
    typeM: str = Query("PAM", description="Tipo de modulación: PAM, QAM, etc."),
    SNR: float = Query(1.0, description="Signal to Noise Ratio"), 
    R: float = Query(1.0, description="Rate"), 
    N: float = Query(1, description="quadrature"),
    n: float = Query(1, description="Code length"),
    th: float = Query(1, description="Threshold"),
):
    """  
    Calcula l'exponent `Pe`, 'E' i `RHO`.
    """
    # Resultat + Retron
    # Allocate output buffer
    result = (ctypes.c_float * 3)()
    lib.exponents(
        ctypes.c_float(M),
        typeM.encode('utf-8'),
        ctypes.c_float(SNR),
        ctypes.c_float(R),
        ctypes.c_float(N),
        ctypes.c_float(n),
        ctypes.c_float(th),
        result  # Pass the buffer
    )
    values = list(result)  # Convert to Python list

    return {
        "Probabilidad de error": values[0],
        "Exponents": values[1],
        "rho óptima": values[2]
    }

# ------------------------ GRAPHICS -------------------------------------------------------------------------
def call_exponents(M: float, typeModulation: str, SNR: float, Rate: float, N: float, n:float, th: float) -> list[float]:
    """
    Wrapper para la función C++ 'exponents' que retorna una lista de 3 valores:
    [Probabilidad de error, Exponent, rho óptima]
    """
    result_ptr = lib.exponents(
        ctypes.c_float(M),
        typeModulation.encode('utf-8'),  # Convertir string a C-style
        ctypes.c_float(SNR),
        ctypes.c_float(Rate),
        ctypes.c_float(N),
        ctypes.c_float(n),
        ctypes.c_float(th)
    )
    return [result_ptr[i] for i in range(3)]

# Classe per la petició de generar una gràfica respecte una funció ja pre-programada
class FunctionPlotRequest(BaseModel):
    y: str
    x: str
    rang_x: list[float]
    points: int
    typeModulation: str
    M: float
    SNR: float
    Rate: float
    N: float
    n: float
    th: float
    color: str = "steelblue"
    lineType: str = "-"
    plotType: str = "linear"

# Endpoint per generar gràfiques a partir de funcions predefinides
@app.post("/plot_function")
async def generate_plot_from_function(plot_data: FunctionPlotRequest):
    try:
        # Generar valores x asegurando enteros para M y N
        if plot_data.x in ["M", "N", "n"]:
            raw = np.linspace(plot_data.rang_x[0], plot_data.rang_x[1], plot_data.points)
            # Redondear a enteros y eliminar duplicados, ordenados
            x_vals = np.unique(np.round(raw).astype(int))
        else:
            x_vals = np.linspace(plot_data.rang_x[0], plot_data.rang_x[1], plot_data.points)

        y_vals = []

        for x_point in x_vals:
            # Ajusta els valors segons la variable independent
            args = {
                "M": plot_data.M,
                "SNR": plot_data.SNR,
                "Rate": plot_data.Rate,
                "N": plot_data.N,
                "n": plot_data.n,
                "th": plot_data.th
            }
            args[plot_data.x] = x_point

            # Allocate a new buffer for each call
            result = (ctypes.c_float * 3)()
            lib.exponents(
                ctypes.c_float(args["M"]),
                plot_data.typeModulation.encode('utf-8'),
                ctypes.c_float(args["SNR"]),
                ctypes.c_float(args["Rate"]),
                ctypes.c_float(args["N"]),
                ctypes.c_float(args["n"]),
                ctypes.c_float(args["th"]),
                result  # Pass the buffer
            )
            y_map = {
                "ErrorProb": result[0],
                "Exponents": result[1],
                "Rho": result[2]
            }
            y_vals.append(y_map[plot_data.y])

        return {
            "x": x_vals.tolist(),
            "y": y_vals
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating plot data: {str(e)}")
    


class ContourPlotRequest(BaseModel):
    y: str
    x1: str
    x2: str
    rang_x1: list[float]
    rang_x2: list[float]
    points: int
    typeModulation: str
    M: float
    SNR: float
    Rate: float
    N: float
    n: float
    th: float

@app.post("/plot_contour")
async def generate_contour_plot(plot_data: ContourPlotRequest):
    try:
        # Generar valores de x1
        if plot_data.x1 in ["M", "N", "n"]:
            raw_x1 = np.linspace(plot_data.rang_x1[0], plot_data.rang_x1[1], plot_data.points)
            x1_vals = np.unique(np.round(raw_x1).astype(int))
        else:
            x1_vals = np.linspace(plot_data.rang_x1[0], plot_data.rang_x1[1], plot_data.points)

        # Generar valores de x2
        if plot_data.x2 in ["M", "N", "n"]:
            raw_x2 = np.linspace(plot_data.rang_x2[0], plot_data.rang_x2[1], plot_data.points)
            x2_vals = np.unique(np.round(raw_x2).astype(int))
        else:
            x2_vals = np.linspace(plot_data.rang_x2[0], plot_data.rang_x2[1], plot_data.points)

        z_matrix = []

        for val1 in x1_vals:
            row = []
            for val2 in x2_vals:
                args = {
                    "M": plot_data.M,
                    "SNR": plot_data.SNR,
                    "Rate": plot_data.Rate,
                    "N": plot_data.N,
                    "n": plot_data.n,
                    "th": plot_data.th
                }
                args[plot_data.x1] = val1
                args[plot_data.x2] = val2

                result = (ctypes.c_float * 3)()
                lib.exponents(
                    ctypes.c_float(args["M"]),
                    plot_data.typeModulation.encode('utf-8'),
                    ctypes.c_float(args["SNR"]),
                    ctypes.c_float(args["Rate"]),
                    ctypes.c_float(args["N"]),
                    ctypes.c_float(args["n"]),
                    ctypes.c_float(args["th"]),
                    result
                )

                y_map = {
                    "ErrorProb": result[0],
                    "Exponents": result[1],
                    "Rho": result[2]
                }
                row.append(y_map[plot_data.y])
            z_matrix.append(row)

        return {
            "x1": x1_vals.tolist(),
            "x2": x2_vals.tolist(),
            "z": z_matrix
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating contour plot: {str(e)}")


# ------------------------ CHATBOT -------------------------------------------------------------------------
class ChatbotRequest(BaseModel):
    message: str

@app.post("/chatbot")
async def chatbot_with_bot(request: ChatbotRequest):
    """
    Endpoint per interactuar amb el chatbot.
    """
    try:
        response = respond(request.message)
        return {"response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in chatbot: {str(e)}")    