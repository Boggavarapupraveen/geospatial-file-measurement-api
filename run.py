import uvicorn

if __name__ == "__main__":
    print("=" * 70)
    print("  Starting Geospatial File Measurement API & Web Explorer")
    print("  Local Web UI & Map : http://localhost:8000")
    print("  Swagger API Docs   : http://localhost:8000/docs")
    print("  ReDoc API Docs     : http://localhost:8000/redoc")
    print("=" * 70)
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
