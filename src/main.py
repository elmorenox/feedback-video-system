from fastapi import FastAPI

app = FastAPI(title="Feedback Video System")

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
