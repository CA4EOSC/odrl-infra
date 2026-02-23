from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
import os
from .routers import dids, vcs, oac, variables, groups, croissants

app = FastAPI(title="ODRL API", description="API wrapper for OYDID CLI with VC Capabilities")

# API Routers with /api prefix
app.include_router(dids.router, prefix="/api")
app.include_router(vcs.router, prefix="/api")
app.include_router(oac.router, prefix="/api")
app.include_router(variables.router, prefix="/api")
app.include_router(groups.router, prefix="/api")
app.include_router(croissants.router, prefix="/api")

@app.get("/api/health")
async def health_check():
    return {"status": "ok", "service": "oydid-api"}

# Serve Frontend Static Files
# Priority 1: Docker build location (outside bind mount)
docker_static_dir = "/frontend_dist"
# Priority 2: Local development location
local_static_dir = os.path.join(os.path.dirname(__file__), "static")

if os.path.exists(docker_static_dir):
    static_dir = docker_static_dir
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
elif os.path.exists(local_static_dir):
    static_dir = local_static_dir
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
else:
    static_dir = None
    print("Warning: Static files not found")

# Catch-all route for SPA (React Router)
@app.exception_handler(404)
async def custom_404_handler(request, __):
    if request.url.path.startswith("/api"):
        return JSONResponse(status_code=404, content={"detail": "Not Found"})

    # Re-evaluate static_dir in case it wasn't set globally or to be safe
    current_static_dir = None
    if os.path.exists(docker_static_dir):
        current_static_dir = docker_static_dir
    elif os.path.exists(local_static_dir):
        current_static_dir = local_static_dir
        
    if current_static_dir and os.path.exists(os.path.join(current_static_dir, "index.html")):
        return FileResponse(os.path.join(current_static_dir, "index.html"))
    return {"detail": "Not Found"}
