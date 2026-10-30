from fasapi import FastAPI

app = FastAPI(title="TaskHub")


@app.get("/health")
def health_check():
    return {"status": "ok"}
