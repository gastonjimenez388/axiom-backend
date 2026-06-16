from fastapi import FastAPI
from fastapi.middleware.cors import CORSMIDDLEWARE

app = FastAPI()

# Esto permite que tu web en aeronexares.com hable con tu backend
app.add_middleware(
    CORSMIDDLEWARE,
    allow_origins=["https://www.aeronexares.com"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"status": "Axiom Backend operativo"}
